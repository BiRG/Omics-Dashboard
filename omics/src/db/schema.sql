/*Note to future maintainer: this DB isn't normalized very well...*/

/*
 This app uses a relational database with this schema to store users,
 user groups, analyses, 

 Workflows and modules are read from yml files
 Collection and sample attributes are read from hdf5 files
 
 SQLite has built in primary keys, (rowid)
 */

 /*
 TODO: date modified in schema with triggers
 */
create table if not exists Users (
    email text not null unique,
    name text,
    password text not null,
    admin integer not null
);

/*
 Multiple collections can be attached to an Analysis
 these analyses are stored in the hdf5 file of the collection as a list
 in a veritable Gertrude Stein's Muenster of properly normalized SQL db
 and poorly-implemented homebrew document-oriented db
 */
create table if not exists Analyses (
    name text,
    description text,
    createdBy integer,
    owner integer,
    groupPermissions text,
    allPermissions text,
    userGroup integer
);

/*
 This table contains group id's and metadata 
 */
create table if not exists UserGroups(
    createdBy integer, /* keep in mind that any group admin can delete group */
    name text,
    description text
);

/*
 Workflows are constructed from workflow modules and defined by yaml files. This is 
 just used to keep track of them
 */
create table if not exists Workflows(
    createdBy integer,
    name text,
    description text
);

/*
 This table contains a mapping of user ids to groups
 */
create table if not exists GroupMemberships(
    userId integer,
    groupMembership integer,
    groupAdmin integer /* Whether user is admin of this group */
);

/*
 Maps analysis ids to groups
 */
create table if not exists AnalysisMemberships(
    analysisId integer,
    groupMembership integer
);

/*
 Maps workflows to analyses
 */
create table if not exists WorkflowMemberships(
    workflowId integer,
    analysisId integer
);

/*
 Maps collections to analyses
*/
create table if not exists CollectionMemberships(
    collectionId integer,
    analysisId integer
);

