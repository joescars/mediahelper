# Publishing mediahelper to an APT repository

## Recommended release flow

1. Cut a release by tagging a commit, for example `v0.1.0`.
2. Let CI build a `.deb` from that tag.
3. Publish the package into an APT repository.
4. Sign the repository metadata with a GPG key.
5. Point users at the repo and let `apt` handle upgrades.

## Good repo options

| Tool | Best for |
| --- | --- |
| `reprepro` | A simple private/public APT repo on a server |
| `aptly` | Snapshot-based publishing and mirrors |
| Package hosting service | Lowest maintenance if you do not want to run repo infrastructure |

## CI/CD pattern

Use two jobs:

1. **Build job** on every pull request, main-branch push, and tag push.
2. **Publish job** only on signed release tags.

The build job should:

1. install Debian packaging dependencies;
2. run `dpkg-buildpackage -us -uc -b`;
3. upload the resulting `.deb` as an artifact or GitHub Release asset.

The publish job should:

1. download the `.deb` artifact;
2. import a GPG signing key from secrets;
3. add the package to your repo (`reprepro includedeb` or `aptly repo add`);
4. publish the repo metadata;
5. optionally upload the package to long-term storage.

## Example with `reprepro`

On the repo server:

```bash
reprepro -b /srv/apt includedeb stable /path/to/mediahelper_0.1.0-1_all.deb
```

You then expose `/srv/apt` over HTTPS and add the repo on client machines:

```bash
echo "deb [signed-by=/usr/share/keyrings/mediahelper.gpg] https://apt.example.com stable main" | sudo tee /etc/apt/sources.list.d/mediahelper.list
sudo apt update
sudo apt install mediahelper
```

## Example with CI and GitHub Releases

If you do not want to run your own repo yet, have CI attach the `.deb` to a GitHub Release for each tag. That gives you a clean release artifact today, and you can later sync those artifacts into an APT repo without changing the package build step.

## Notes

- You will need a real license file before public distribution.
- For public repos, keep package versions semantic and stable.
- Rebuild the repo metadata whenever you publish a new package.
