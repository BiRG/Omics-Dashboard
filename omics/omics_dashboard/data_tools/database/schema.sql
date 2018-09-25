/*Note to future maintainer: this DB isn't normalized very well...*/

/*
 This omics_dashboard uses a relational database with this schema to store users,
 user groups, analyses.py,

 Workflows and modules are read from yml files
 Collection and sample attributes are read from hdf5 files
 
 SQLite has built in primary keys, (rowid)
 */

 /*
 TODO: date modified in schema with triggers
 */
create table if not exists Users (
    id integer primary key,
    email text not null unique,
    name text,
    password text not null,
    admin integer not null
);

/*
 Multiple collections can be attached to an Analysis
 these analyses.py are stored in the hdf5 file of the collection as a list
 in a veritable Gertrude Stein's Muenster of properly normalized SQL database
 and poorly-implemented homebrew document-oriented database
 */
create table if not exists Analyses (
    id integer primary key,
    name text,
    description text,
    createdBy integer,
    owner integer,
    groupPermissions text,
    allPermissions text,
    userGroup integer
);

/*
  Samples can be grouped while remaining distinct. A collection is a concatenation/merging
  of samples following a particular order.
 */
create table if not exists SampleGroups(
    id integer primary key,
    name text,
    description text,
    createdBy integer,
    owner integer,
    groupPermissions text,
    allPermissions text,
    userGroup integer,
    uploadWorkflowId text
);

/*
 This table contains group id's and metadata 
 */
create table if not exists UserGroups(
    id integer primary key,
    createdBy integer, /* keep in mind that any group admin can delete group */
    name text,
    description text
);

/*
 Workflows are constructed from workflow modules and defined by yaml files. This is 
 just used to keep track of them
 */
create table if not exists Workflows(
    id integer primary key,
    name text,
    description text,
    owner integer,
    createdBy integer,
    userGroup integer,
    groupPermissions text,
    allPermissions text
);

create table if not exists JobServerTokens(
    id integer primary key,
    value text
);

create table if not exists Invitations(
    id integer primary key,
    createdBy integer,
    value text
);
/*
 This table contains a mapping of user ids to groups
 */
create table if not exists GroupMemberships(
    userId integer,
    groupId integer,
    groupAdmin integer, /* Whether user is admin of this group */
    unique(userId, groupId)
);

/*
 Maps analysis ids to groups
 */
create table if not exists AnalysisMemberships(
    analysisId integer,
    groupId integer,
    unique(analysisId, groupId)
);

/*
 Maps workflows to analyses.py
 */
create table if not exists WorkflowMemberships(
    workflowId integer,
    analysisId integer,
    unique(workflowId, analysisId)
);

/*
 Maps collections to analyses.py
*/
create table if not exists CollectionMemberships(
    collectionId integer,
    analysisId integer,
    unique(collectionId, analysisId)
);

create table if not exists SampleGroupMemberships(
    sampleId integer,
    sampleGroupId integer,
    unique(sampleId, sampleGroupId)
);
