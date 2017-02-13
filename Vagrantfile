# -*- mode: ruby -*-
# vi: set ft=ruby :

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.
#

require_relative './provisioning/vagrant/key_authorization'

Vagrant.configure(2) do |config|
    # The most common configuration options are documented and commented below.
    # For a complete reference, please see the online documentation at
    # https://docs.vagrantup.com.
    #

    # Add the current user key inside the machine so that SSH is easy.
    # (useful for running ansible on the VM)
    authorize_key_for_root config, '~/.ssh/id_rsa.pub'

    config.vm.box = "debian/jessie64"

    config.vm.provision :shell, path: "provisioning/bootstrap.sh"
    config.vm.network "private_network", ip: "192.168.33.10"

    # Useful with: https://github.com/cogitatio/vagrant-hostsupdater
    config.vm.hostname = "app.mangaki.dev"
    config.vm.provider "virtualbox" do |vb|
        vb.name = "Mangaki"
    end
end
