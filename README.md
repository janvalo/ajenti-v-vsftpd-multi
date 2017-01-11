#VSFTPD support for Ajenti V
Allows for a simple management of multiple users per domain using VSFTP.
This plugin is extended version of the original plugin created by Eugene Pankov <e@ajenti.org> that is included with the original installation of Ajenti V.

#Installation

Before the installation you will need to remove the installed FTP plugin from '''/var/lib/ajenti/plugins/'''. Normally it should be either '''vh-vsftpd''' or '''vh-pureftpd'''.

Now clone this repo directly to plugins folder '''/var/lib/ajenti/plugins/'''

    git clone https://github.com/jvalo/ajenti-v-vsftpd-multi

We will need to install few dependencies:

    sudo apt-get install vsftpd openssl libpam-pwdfile

Then restart Ajenti

    service ajenti restart

#Contribution

Feel free to fork this repo or make a PR for any improvements :)
