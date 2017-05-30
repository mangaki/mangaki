# -*- mode: ruby -*-
# vi: set ft=ruby :

require 'time'

# All Vagrant configuration is done below. The "2" in Vagrant.configure
# configures the configuration version (we support older styles for
# backwards compatibility). Please don't change it unless you know what
# you're doing.
#

Vagrant.configure(2) do |config|
    # The most common configuration options are documented and commented below.
    # For a complete reference, please see the online documentation at
    # https://docs.vagrantup.com.
    #
    config.vm.box = "debian/contrib-jessie64"

    config.vm.synced_folder ".", "/vagrant"

    config.vm.provision "ansible" do |ansible|
	ansible.inventory_path = "provisioning/inventories/vagrant/hosts"
        ansible.playbook = "provisioning/site.yml"
	ansible.extra_vars = {
	  mangaki_sync_migrate: true,
	  mangaki_sync_collectstatic: false,
	  mangaki_sync_load_seed: true,
	}
    end

    # Provisioner for dumping the database
    config.vm.provision "dumpdb", type: "ansible", run: "never" do |ansible|
	ansible.inventory_path = "provisioning/inventories/vagrant/hosts"
        ansible.playbook = "provisioning/site.yml"
	ansible.tags = ['action']
	ansible.extra_vars = {
	  mangaki_db_dump: true,
	  mangaki_db_dump_path_local: "pgdumps/vagrant/mangaki-#{Time.now.utc.iso8601}.pgdump",
	}
    end

    config.vm.network "private_network", ip: "192.168.33.10"

    # Useful with: https://github.com/cogitatio/vagrant-hostsupdater
    config.vm.hostname = "mangaki.dev"
    config.vm.provider "virtualbox" do |vb|
        vb.name = "Mangaki"
    end
end
