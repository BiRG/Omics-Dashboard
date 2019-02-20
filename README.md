# Omics Dashboard

A multiuser web-based data management and pipelining tool for systems biology workflows.

Omics Dashboard consists of a web service for managing data and workflows, and the [Cromwell workflow engine](https://github.com/broadinstitute/cromwell) from the [Broad Institute](https://www.broadinstitute.org/) for executing CWL (and eventually WDL) workflows. Omics Dashboard can be deployed from bare metal or various cloud services and is primarily intended for managing "small" metabolomics datasets (< 1 GB), though it eventually can be modified to deal with larger data. Omics Dashboard can accomodate multiple users with controlled access to data.

## Getting Started
Omics Dashboard can be deployed in several ways. The easiest way is via [Docker Compose](https://docs.docker.com/compose/).

On any machine with Docker and Docker Compose:
1. Copy `.env-example` to `.env` and change the `MODULEDIR` variable to match the location of the repo's `modules` directory.
2. Copy `common-example.env` to `common.env`. If you intend to deploy Omics Dashboard on a publicly-accessible server, you should change `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD` and `SECRET` to secure passwords.
3. Run `docker-compose up` from the root of the repo and navigate to [localhost:8080/omics/](http://localhost:8080/omics). The default username is `admin@admin.admin` and the default password is `password`. You should change the email address and password of this default user or create a new user, grant the user admin privelege, then delete the default user as the new user.
4. To use in a publicly-facing context, see the configuration information below.

## Configuration
Only two files are used to configure Omics Dashboard when deploying with Docker Compose: `common.env`, defines the environment variables in the application containers and `.env` defines the environment variables during the container build process.
The following variables may be changed, but only `OMICSSERVER`, `SECRET`, `MYSQL_PASSWORD`, `MYSQL_ROOT_PASSWORD`, `MODULEDIR` and `BRAND` have to be changed in most installations.

| Variable              | File                 | Description                                                                                                               |
|-----------------------|----------------------|---------------------------------------------------------------------------------------------------------------------------|
| `COMPUTESERVER`       | `common.env`         | The url of the compute server. Only change if you are hosting a Cromwell server outside of the Docker Compose network.    |
| `SECRET`              | `common.env`         | A secret used for securing passwords, tokens and sessions. You must change this for your installation to be secure.       |
| `BRAND`               | `common.env`         | Some text displayed in the navigation bar of the app. Should be changed to your organization's name.                      |
| `DATADIR`             | `common.env`         | The path relative to the omics server to store data. Should usually not be changed                                        |
| `MODULEDIR`           | `common.env`, `.env` | The path relative to the omics server to store CWL tool definitions. Should usually not be changed                        |
| `OMICSSERVER`         | `common.env`, `.env` | The url of the Omics Dashboard server relative to the end user (what you would enter into the browser).                   |
| `MYSQL_DATABASE`      | `common.env`         | The name of the MariaDB (or MySQL) database used by the Cromwell jobserver. Should usually not be changed.                |
| `MYSQL_USER`          | `common.env`         | The name of the MariaDB (or MySQL) database user. Should usually not be changed                                           |
| `MYSQL_PASSWORD`      | `common.env`, `.env` | The password for the MariaDB (or MySQL) database used by the jobserver. Should be changed to a securely-generated secret. |
| `MYSQL_ROOT_PASSWORD` | `common.env`         | The password for the MariaDB (or MySQL) database root user.                                                               |
| `DB_URI`              | `common.env`         | The URI of the database used by the omics service. By default, a SQLite database is created in the data directory         |
| `HOSTPORT`            | `.env`               | The port on the host you want to access the service from. Should be consistent with `OMICSSERVER`                         |

## Documentation
Documentation for Omics Dashboard is located on the [wiki](https://github.com/BiRG/Omics-Dashboard/wiki) of the GitHub repository.

## Licensing
Omics-Dashboard is licensed under the terms of the [AGPL v3](https://choosealicense.com/licenses/agpl-3.0/). This is a very restrictive and "infectious" license. Since the configuration for Omics-Dashboard frequently involves changing the source code itself, it may not be possible to use Omics-Dashboard without making your modifications available to all users of your deployment. If this presents a problem, please contact the maintainers. Licensing under more permissive terms is available upon request and will most likely be granted for nearly any use case outside of operating Omics-Dashbaord as a commercial service.

## Bug Reports & Feature Requests
We use GitHub issues to track public bugs. Report a bug by [opening a new issue](https://github.com/BiRG/Omics-Dashboard/issues/new/choose). Good issues should follow the templates provided.
