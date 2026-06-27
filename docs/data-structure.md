# Data structure in "rezepte" db

Data are stored in a [mongo db](https://www.mongodb.com/docs/).
Every element can be formed as [json](https://de.wikipedia.org/wiki/JSON) data structure.

## Recipes

Recipe structure is organized as followed

```json
{
    "_id": ....,
    "group_id": <id of recipe group>,
    "name": "<name of recipe>",
    "tag_ids": [
        <id of tag>,
        ....
    ],
    "source": "<source of recipe e.g. web site link or reference to book>",
    "required-time": "<estimate of time to create recipe>",
    "ingredients": "<list of ingredients in markdown format>",
    "instructions": "<enumeration of instructions to prepare recipe in markdown format>",
    "amount": <number>,
    "amount-name" "<name of amount like portions>",
    "remarks": "<addtional remarks in markdown format>",
    "images": [
        <list of image id>
    ],
    "changes": [
        {
            "user-name": "<user name of author>",
            "time": <change time in UTC format>
        },
        ....
    ]
}
```

## Group

Recipes are assigned to recipe groups. These groups shall be used to enable
multiple access areas or recipe books, e.g. family receipes, recipes for Meret,
recipes for ....

Access rights shall be granted per group, so it is possible that user John has
adin rights for group A, editor right for groups C and E and "only" reader rights
for all other groups

Groups are defined in following structure ...

```json
{
    "_id": ....,
    "name": "<name of group>",
    "changes": [
        {
            "user-name": "<user name of author>",
            "time": <change time in UTC format>
        },
        ....
    ]

}
```

## User

User administration uses Keycload functionality for user authentication.
But every user can get different roles in different recipe books or recipe
groups. So an extra adminstration is needed to handle user rights for
different groups.

Proposed structure is

```json
{
    "_id": ...
    "user_name": "user name",
    "access": [
        "group_id": <group_id>,
        "access": "<access>"
    ]
}
```

`<access>` are related access rights. Following options are possiple...

- `reader`: can read all recipes in for thos group
- `author`: same as `reader`, but can also add, edit and delete recipes
- `admin`: same as `author`, but can also user adminstration for this group
  - user adminstration means
    - add user and assign them to the group
    - add existing user to the group
    - remove user assignment from tge group

In addtion to all this group speific rules exists also an access right `super-admin`.
User with thi access category have `admin`right for all groups. In this case
`"group_id"` will be ignore.

## pictures

One or more picture can be assign to a recipe.

```json
{
    "_id": ...,
    "s3_id": .....,
    "thumbnail_s3_id": ....
}
```

## Tags

A list of tags can be assigned to every recipes. Tags can be used to characterize
or categorize a recipes and enables a fast and easy way to find recipes.

Tags are defined in following structure ...

```json
{
    "_id": ....,
    "name": "<name of tag>",
    "changes": [
        {
            "user-name": "<user name of author>",
            "time": <change time in UTC format>
        },
        ....
    ]

}
```
