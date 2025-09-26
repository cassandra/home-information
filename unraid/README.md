# Unraid Installation Guide

Home Information is available as a Community App for Unraid systems.

## Quick Install (Recommended)

1. **Install Community Applications Plugin** (if not already installed):
   - Go to Apps tab in Unraid
   - Install "Community Applications" by squid

2. **Search for Home Information**:
   - Apps tab → Search for "Home Information"
   - Click "Install"

3. **Configure Settings**:
   - **IMPORTANT**: Change the Django Secret Key to a random string
   - **IMPORTANT**: Change the admin password from default
   - Adjust port if 9411 conflicts with other services
   - Review storage paths (defaults are fine for most users)

4. **Access**: http://YOUR-UNRAID-IP:9411

## Manual Installation

If the app isn't in Community Apps yet, you can install manually:

1. **Apps tab** → **Previous Apps** → **Add Container**
2. **Template URL**: `https://raw.githubusercontent.com/cassandra/home-information/master/unraid/home-information.xml`
3. Click **Add Container**
4. Configure settings as above

## Configuration Details

### Required Settings
- **Django Secret Key**: Generate a random 50-character string for security
- **Admin Password**: Change from default for security

### Storage Paths
- **Database**: `/mnt/user/appdata/home-information/database` (SQLite database)
- **Media**: `/mnt/user/appdata/home-information/media` (uploaded files)
- **Config**: `/mnt/user/appdata/home-information/env` (optional environment files)

### Network Settings
- **Port**: 9411 (default, change if needed)
- **Network**: Bridge mode (recommended)

## Integrations

### Home Assistant
If you're running Home Assistant on Unraid:
1. Note your Home Assistant URL (e.g., `http://192.168.1.100:8123`)
2. In Home Information, go to Settings → Integrations
3. Add Home Assistant integration with your URL and access token

### ZoneMinder
If you're running ZoneMinder on Unraid:
1. Note your ZoneMinder URL (e.g., `http://192.168.1.100:8080/zm`)
2. In Home Information, go to Settings → Integrations
3. Add ZoneMinder integration with your URL and credentials

## Troubleshooting

### Container Won't Start
- Check Unraid logs: `docker logs home-information`
- Ensure storage paths are writable
- Verify no port conflicts

### Can't Access WebUI
- Check container is running
- Verify port mapping (default 9411)
- Check firewall settings

### Authentication Issues
- Default: Authentication is disabled for local network use
- To enable: Set `HI_SUPPRESS_AUTHENTICATION` to `false`

## Security Notes

- **Local Network Only**: By default, authentication is disabled for convenience on local networks
- **Change Defaults**: Always change the Django secret key and admin password
- **Firewall**: Don't expose port 9411 to the internet without proper authentication

## Support

- **GitHub**: https://github.com/cassandra/home-information/issues
- **Documentation**: https://github.com/cassandra/home-information/tree/master/docs
- **Unraid Forum**: Search for "Home Information" in Community Apps support