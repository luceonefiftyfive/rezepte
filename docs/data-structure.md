# Data structure in rezepze db

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
    "remarks": "<addtional remarks in markdown format>",
    "images": [
        <list of image references>
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

## Groups

Recipes are assigned to recipe group. These groups shall be used to enable
multiple access areas, e.g. family receipes, recipes for Meret, recipes for ....

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

Name of groups is used as well to defined access realm.

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
