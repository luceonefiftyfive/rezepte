# Creating a Release

## 1. Select the Release Version

Choose the new version according to [Semantic Versioning](https://semver.org):

- **PATCH** (1.3.0 → 1.3.1): backward-compatible bug fixes
- **MINOR** (1.3.1 → 1.4.0): new backward-compatible functionality
- **MAJOR** (1.4.0 → 2.0.0): incompatible or breaking changes

## 3. Update the Changelog

Update the version content in [Changelog.md](../Changelog.md):

## 4. Update the Version File

Update the version in [version.yaml](../version.yaml):

```yaml
version: 0.4.1
```

## 5. Commit the Changes

Add and commit the updated version file:

```bash
git add version.yaml Changelog.md
git commit -m "chore(release): prepare version 0.4.1"
```

## 6. Create the Git Tag

Create an annotated tag for the release:

```bash
git tag -a v0.4.1 -m "Release version 0.4.1"
```

## 7. Push the Commit and Tag

Push the commit and the new tag to the remote repository:

```bash
git push origin HEAD
git push origin --tags
```

Alternatively, push the commit and all loca
