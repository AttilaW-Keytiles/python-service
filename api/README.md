# What is here?

In this folder you find OpenApi definitions of our different APIs.

# API versioning policy

We follow [Semantic versioning](https://semver.org/) - but no patch versions(!) - with the APIs. The version of the API you always find at the place defined by Open API /info/version JSON path.

# File naming strategy (lean versioning)

However API version is always "major.minor" format in file naming we follow slightly different strategy.

1. The most recent API of a major version is always kept in a file which is postfixed with the major version only using "-v{major}".
1. When a file name contains "-v{major}.{minor}" version then this file is NOT the most recent one in major version but kind of an archived minor version. We keep them only for easier diff possibility so by comparing it to the "-v{major}" postfixed file name (or any other "-v{major}.{minor}") you can find the changes easier in between those two. This is very useful during upgrading your Client.

# Generating models

Once you changed the API you need to generate code from it. Use the [generate-models.sh](generate-models.sh) script for that!

**NOTE!** Depending on your change you also might need to update the [generate-models.sh](generate-models.sh) script! E.g. when you introduce a new major version...

