# Contributing to Mangaki

Mangaki is an open source project which is managed by a French non-profit, our objective is to make people aware of new works which are usually unknown.

We are still working out the details to make contributing to the project as easy and transparent as possible, but we are not quite there yet.

Hopefully this document makes the process for contributing clear and answers some questions that you might have.

## [Code of Conduct](./CODE_OF_CONDUCT.md)

Mangaki has adopted a Code of Conduct that we expect project participants to adhere to. Please read [the full text](./CODE_OF_CONDUCT.md) so that you can understand what actions will and will not be tolerated.

## Our development process

The core team will be working directly on GitHub, these changes will be public from the beginning.

## `master` is unsafe

We will do our best to keep `master` in good shape, with tests (when we will have them!) passing at all times.
But we are human, and we want to move fast, so we might do core changes (Database schema, configuration schema, …) that makes your code incompatible with.
We will do our best to communicate these changes and always version appropriately so you can lock into a specific version if need be.

### Test Suite

Currently, we don't have tests (07/12/2016).

Some team members are working on them and will populate this part once the tests are merged in `master`.

### Pull Requests

**Working on your first Pull Request?** You can learn how from this *free* series [How to Contribute to an Open Source Project on GitHub](https://egghead.io/series/how-to-contribute-to-an-open-source-project-on-github)

The core team will be monitoring for pull requests. When we get one, we'll let our test suite check if everything is in order. From here, we will need to get another person to validate and sign off on the changes and then merge the pull request. As for breaking changes, we might need to fix internal uses (our instances), which could cause some delay.

We'll do our best to provide updates and feedback throughout the process.

Before submitting a pull request, please make sure the following is done:

1. Fork the repository and create your branch from `master`
2. If you've added code that should be tested, add tests!
3. If you've changed APIs, update the documentation.
4. Ensure the test suite passes.
5. Make sure your code lints and respect the PEP8 and [Standard JavaScript style](http://standardjs.com/).
6. Ensure your branch is rebased on the latest `master` to facilitate merges.

When we accept your pull request, we will squash all your commits to simplify our history and conserve your branch history if necessary.

## Bugs

### Where to Find Known Issues

We will be using GitHub Issues for our public bugs.
Before filing a new task, try to make sure that your problem doesn't already exist.

### Reporting New Issues

The best way to get your bug fixed is to provide a reduced test case:

1. If you can reproduce the issue on <mangaki.fr> or your local installation, explain us the steps to reproduce it with the URL and screenshots.
2. If you have difficulties with configuration, installation process, explain us the steps you have taken and put carefully each command output you used so we can help you efficiently.

You can also fill issues for ideas, requests and more!
Don't hesitate to open an issue! Our team is always more than happy to discuss with your thoughts!

### Security Bugs

If you think you found a security bug, please email <security@mangaki.fr> for the safe disclosure of security bugs.
With that in mind, please do not file public issues.

## How to Get in Touch

- IRC – #anime on ulminfo.fr
- Twitter – [MangakiFR](https://twitter.com/MangakiFR)
- Discussion forum — [meta.mangaki.fr](http://meta.mangaki.fr)
- Email — <developers@mangaki.fr>

## Style Guide

Our linter will catch most styling issues that may exist in your code.
You can check the status of your code styling:

- For Python, run `flake8 --ignore E501 .` in the root of the repository.
- For JavaScript, run `eslint .` in the root of the repository.

However, there are still some styles that the linter cannot pick up. If you are unsure about something:

- For Python, looking at [PEP8](https://www.python.org/dev/peps/pep-0008/) will guide you in the right direction.
- For JavaScript, looking at [Standard Code Style](http://standardjs.com/) will guide you in the right direction.

## Licence

By contributing to Mangaki, you agree that your contributions will be licensed under its AGPLv3 licence.
