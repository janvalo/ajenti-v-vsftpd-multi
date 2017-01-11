import os
import subprocess
import shutil
import tempfile
import uuid
import json

from ajenti.api import *
from ajenti.ui import on
from ajenti.ui.binder import Binder
from ajenti.util import platform_select

from ajenti.plugins.services.api import ServiceMultiplexor
from ajenti.plugins.vh.api import MiscComponent
from ajenti.plugins.vh.extensions import BaseExtension


@plugin
class VSFTPDExtension (BaseExtension):
    default_config = {
        'users': [],
    }
    name = 'FTP'

    def init(self):
        self.append(self.ui.inflate('ajenti-v-vsftpd-multi:ext'))
        self.binder = Binder(self, self)
        self.refresh()

    def refresh(self):
        if not 'users' in self.config:
            if not self.config['created']:
                self.config['users'] = [{
                    'name': self.website.slug + '_admin',
                    'username': self.website.slug + '_admin',
                    'password': str(uuid.uuid4()),
                    'ftp-path': self.website.root
                }]
                self.config['created'] = True
            else:
                self.config['users'] = []

            dirs = os.listdir("/etc/vsftpd.users.d")
            for users in dirs:
                if self.website.slug in users:
                    self.config['users'].append({
                        'name': users,
                        'username': users,
                        'password': '',
                        'ftp-path': self.website.root
                    })

        self.binder.setup().populate()
        self.find('ftp-username').value = self.website.slug + '_user'+ str(len(self.config['users']) + 1)
        self.find('ftp-password').value = str(uuid.uuid4())
        self.find('ftp-new-path').value = self.website.root

        self.find('users').delete_item = lambda i, c: self.on_delete_user(i)


    def update(self):
        self.binder.update()

    @on('create-user', 'click')
    def on_create_user(self):

        username = self.find('ftp-username').value
        password = self.find('ftp-password').value
        path = self.find('ftp-new-path').value

        user_cfg = {
            'name': username,
            'username': username,
            'password': password,
            'ftp-path': path
        }

        self.config['users'].append(user_cfg)
        self.refresh()
        self.try_save()

    def on_delete_user(self, user_cfg):

        self.config['users'].remove(user_cfg)
        self.refresh()
        self.try_save()

    def try_save(self):
        if self.editor_ui is not None:
            self.editor_ui.save_data()


FTP_BANNER = """
========================= (o_o) ==========================

                 Welcome to our FTP Server 

==========================================================

"""


TEMPLATE_CONFIG = """
listen=YES
anonymous_enable=NO
local_enable=YES
guest_enable=YES
guest_username=www-data
nopriv_user=www-data
anon_root=/
xferlog_enable=YES
virtual_use_local_privs=YES
pam_service_name=vsftpd_virtual
user_config_dir=%s
chroot_local_user=YES
hide_ids=YES

banner_file=/etc/banners/ftp.msg

force_dot_files=YES
local_umask=002
chmod_enable=YES
file_open_mode=0755

seccomp_sandbox=NO

"""

TEMPLATE_PAM = """#%%PAM-1.0
auth    required    pam_pwdfile.so pwdfile /etc/vsftpd/ftpd.passwd
account required    pam_permit.so
session required    pam_loginuid.so
"""

TEMPLATE_USER = """
local_root=%(root)s
allow_writeable_chroot=YES
write_enable=YES
"""


@plugin
class VSFTPD (MiscComponent):
    config_root = '/etc/vsftpd'
    config_root_users = '/etc/vsftpd.users.d'
    config_file = platform_select(
        debian='/etc/vsftpd.conf',
        arch='/etc/vsftpd.conf',
        centos='/etc/vsftpd/vsftpd.conf',
    )
    userdb_path = '/etc/vsftpd/ftpd.passwd'
    pam_path = '/etc/pam.d/vsftpd_virtual'

    def create_configuration(self, config):
        if not os.path.exists(self.config_root):
            os.mkdir(self.config_root)
        if os.path.exists(self.config_root_users):
            shutil.rmtree(self.config_root_users)
        os.mkdir(self.config_root_users)

        pwfile = tempfile.NamedTemporaryFile(delete=False)
        pwpath = pwfile.name
        for website in config.websites:
            subprocess.call(['chgrp', 'ftp', website.root])
            subprocess.call(['chmod', 'g+w', website.root])
            if website.enabled:
                cfg = website.extension_configs.get(VSFTPDExtension.classname)
                if cfg is not None:
                    for ftp in cfg['users']:
                        proc = subprocess.Popen(['openssl','passwd','-1', '-noverify', ftp['password']], stdout = subprocess.PIPE)
                        generated_pw = proc.stdout.read()

                        if len(ftp['password']) > 0:
                            pwfile.write('%s:%s\n' % (ftp['username'], generated_pw))

                        open(os.path.join(self.config_root_users, ftp['username']), 'w').write(
                            TEMPLATE_USER % {
                                'root': ftp['ftp-path'],
                            }
                        )
        pwfile.close()
        os.rename(self.userdb_path, self.userdb_path + '.bak')
        shutil.copy(pwpath, self.userdb_path)
        os.unlink(pwpath)
        open(self.pam_path, 'w').write(TEMPLATE_PAM)
        open('/etc/banners/ftp.msg', 'w').write(FTP_BANNER)
        open(self.config_file, 'w').write(TEMPLATE_CONFIG % self.config_root_users)

        if not os.path.exists('/var/www'):
            os.mkdir('/var/www')
        subprocess.call(['chown', 'www-data:', '/var/www'])

    def apply_configuration(self):
        ServiceMultiplexor.get().get_one('vsftpd').restart()
