OpenAFS Buildbot Configuration
==============================

Ansible playbook to deploy and manage the [OpenAFS][1] [Buildbot][2].

Install the required [buildbot roles][4] with `ansible-galaxy`:

    ansible-galaxy collection install openafs_contrib.buildbot

The user and worker passwords are encrypted with `ansible-vault`.

See [wiki.openafs.org][3] for more information.

[1]: https://www.openafs.org/
[2]: https://buildbot.openafs.org/
[3]: https://wiki.openafs.org/devel/buildbotmasternotes/
[4]: https://galaxy.ansible.com/openafs_contrib/buildbot
