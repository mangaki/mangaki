# -*- mode: ruby -*-
# vi: set ft=ruby :

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.
Vagrant.configure(2) do |config|
    # The most common configuration options are documented and commented below.
    # For a complete reference, please see the online documentation at
    # https://docs.vagrantup.com.

    config.vm.box = "ubuntu/trusty64"

    config.vm.network "private_network", ip: "10.99.42.10"

    config.vm.provision :shell, path: "provisioning/bootstrap.sh"

    config.vm.provider "virtualbox" do |vb|
        vb.name = "Mangaki"
    end
end
