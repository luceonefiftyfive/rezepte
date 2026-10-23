# Creating a Release

## 1. Select the Release Version

Choose the new version according to [Semantic Versioning](https://semver.org):

- **PATCH** (1.3.0 → 1.3.1): backward-compatible bug fixes
- **MINOR** (1.3.1 → 1.4.0): new backward-compatible functionality
- **MAJOR** (1.4.0 → 2.0.0): incompatible or breaking changes

Check the current version in [version.yaml](../version.yaml) and choose the next version.

## 2. Update the Changelog

Add the release notes to [Changelog.md](../Changelog.md). Move the completed release
entries out of the `Unreleased` section and add a heading containing the release
version.

## 3. Update the Version File

Set the new version in [version.yaml](../version.yaml):

```yaml
version: <new-version>
```

## 4. Commit the Changes

Review and commit the changelog and version file:

```bash
git add version.yaml Changelog.md
git commit -m "chore(release): prepare version <new-version>"
```

## 5. Create the Git Tag

Create an annotated tag using the `v` prefix:

```bash
git tag -a v<new-version> -m "Release version <new-version>"
```

## 6. Push the Commit and Tag

Push the release commit and tag to the remote repository:

```bash
git push origin HEAD
git push origin v<new-version>
```
