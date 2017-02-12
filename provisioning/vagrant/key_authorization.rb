def authorize_key_for_root(config, *key_paths)
  [*key_paths, nil].each do |key_path|
    if key_path.nil?
      fail "Public key not found at following paths: #{key_paths.join(', ')}"
    end

    full_key_path = File.expand_path(key_path)

    if File.exists?(full_key_path)
      config.vm.provision 'file',
        run: 'once',
        source: full_key_path,
        destination: '/home/vagrant/root_pubkey'

      config.vm.provision 'shell',
        privileged: true,
        run: 'once',
        inline:
          "echo \"Creating /root/.ssh/authorized_keys with #{key_path}\" && " +
          'rm -f /root/.ssh/authorized_keys && ' +
          'mkdir -p /root/.ssh/ &&' + 
          'mv /home/vagrant/root_pubkey /root/.ssh/authorized_keys && ' +
          'chown root:root /root/.ssh/authorized_keys && ' +
          'chmod 600 /root/.ssh/authorized_keys && ' +
          'rm -f /home/vagrant/root_pubkey && ' +
          'echo "Done!"'
      break
    end
  end
end
