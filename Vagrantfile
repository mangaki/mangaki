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
    config.vm.box_check_update = true

    config.vm.network :forwarded_port, guest: 80, host: 8080 # Mangaki web server
    config.vm.network "private_network", ip: "192.168.42.10"

    config.vm.synced_folder ".", "/mnt/mangaki"

    config.vm.define :mangaki do |mangaki|
    end

    config.vm.provision "ansible" do |ansible|
        ansible.verbose = "v"
        ansible.playbook = "provisioning/playbook.yml"
        ansible.sudo = true
    end

    config.vm.provider "virtualbox" do |vb|
        # The Mangaki VM !
        vb.name = "Mangaki"
        # 1 GB seems to be okay.
        vb.memory = "1024"
    end
end
