# Contribution guide

Contributions are welcome! :smile: 

## Instructions

1. Fork the repo to your own GitHub account, click the "Fork" button at the top:

![image](https://github.com/kushalkolar/fastplotlib/assets/9403332/82612021-37b2-48dd-b7e4-01a919535c17)

2. Clone the repo and install according to the development instructions. Replace the `YOUR_ACCOUNT` in the repo URL to the fork on your account.  Note that fastplotlib uses [git-lfs](https://git-lfs.com) for storing large files, so you will need to [install it](https://github.com/git-lfs/git-lfs#installing) before cloning the repo.

```bash
git clone https://github.com/YOUR_ACCOUNT/fastplotlib.git
cd fastplotlib

# install all extras in place
pip install -e ".[notebook,docs,tests]
```

> If you cloned before installing `git-lfs`, you can run `git lfs pull` at any
> time to properly download files.

3. Checkout the `main` branch, and then checkout your feature or bug fix branch, and run tests:

> **Warning**
> Do not commit or add any changes from `examples/desktop/screenshots`.
> If you are creating new test examples that generate or change screenshots please post an issue on the repo and we will help you. The screenshots will be generated on github actions servers, which you can then copy into the screenshots dir. :)

```bash
cd fastplotlib

git checkout main

# checkout your new branch from main
git checkout -b my-new-feature-branch

# make your changes
# run tests
REGENERATE_SCREENSHOTS=1 pytest -v -k examples

# make some changes, lint with black, and commit
black .

# add only your changed files, not the entire repo, do not add changes to examples/screenshots
git add my_changed_files

# commit changes
git commit -m "my new feature"

# push changes to your fork
git push origin my-new-feature-branch
```

4. Finally make a **draft** PR against the `main` branch. When you think the PR is ready, mark it for review to trigger tests using our CI pipeline. If you need to make changes, please set the PR to a draft when pushing further commits until it's ready for review scion. We will get back to your with any further suggestions!
