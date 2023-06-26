# Contribution guide

Contributions are welcome!

## Instructions

1. Fork the repo to your own GitHub account, click the "Fork" button at the top:

![image](https://github.com/kushalkolar/fastplotlib/assets/9403332/82612021-37b2-48dd-b7e4-01a919535c17)

2. Clone the repo and install according to the development instructions. Replace the `YOUR_ACCOUNT` in the repo URL to the fork on your account:

```bash
git clone https://github.com/YOUR_ACCOUNT/fastplotlib.git
cd fastplotlib

# install all extras in place
pip install -e ".[notebook,docs,tests]
```

3. Checkout the `master` branch, and then checkout your feature or bug fix branch, and run tests:

> **Warning**
> Do not commit or add any changes from `examples/screenshots` or `examples/diffs`. 
> If you are creating new test examples that generate or change screenshots please post an issue on the repo and we will help you. 

```bash
cd fastplotlib

git checkout master

# checkout your new branch from master
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

4. Finally make a **draft** PR against the `master` branch. When you think the PR is ready, mark it for review to trigger tests using our CI pipeline. If you need to make changes, please set the PR to a draft when pushing further commits until it's ready for review scion. We will get back to your with any further suggestions!
