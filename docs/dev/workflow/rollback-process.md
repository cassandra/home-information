# Rollback Process

This document outlines the process for rolling back a problematic release of Home Information.

## When to Rollback vs Hotfix

### Rollback When:
- **Critical security vulnerability** in the new release
- **Data corruption** or **database issues** 
- **Application won't start** or crashes immediately
- **Major functionality broken** affecting core features
- **Issue affects all/most users** and no quick fix available

### Hotfix When:
- **Minor bugs** that don't prevent normal operation
- **Issues affecting subset of users** or specific configurations
- **Quick fix available** (< 2 hours to implement and test)
- **Non-critical performance degradation**

**When in doubt, rollback first** - it's easier to rollback immediately and then decide on a fix than to wait and have more users affected.

## Rollback Execution

### Prerequisites
- Identify the **last known good version** (check previous releases)
- Confirm the **problematic version** that needs to be rolled back
- Have **admin access** to the GitHub repository

### Step-by-Step Process

1. **Navigate to GitHub Actions**
   - Go to: `https://github.com/cassandra/home-information/actions`
   - Click on "Rollback Release" workflow

2. **Trigger Manual Rollback**
   - Click "Run workflow" button
   - Fill in required inputs:
     - **Rollback to version**: Previous good version (e.g., `v1.0.1`)
     - **Bad version**: Problematic version to mark (e.g., `v1.0.2`) 
     - **Reason**: Brief description (e.g., "Critical database migration issue")
   - Click "Run workflow"

3. **Monitor Execution**
   - Watch the workflow progress
   - Ensure all steps complete successfully
   - Check for any error messages

4. **Verify Rollback**
   - Confirm Docker `latest` tag points to rollback version
   - Verify bad release is marked "DO NOT USE"
   - Check that tracking issue was created

### What the Rollback Does Automatically

The rollback workflow will:
- Pull the target rollback version from registry
- Re-tag it as `latest` 
- Push updated `latest` tag
- Mark bad release with "DO NOT USE - ROLLED BACK" warning
- Update release notes with warning and update instructions
- Mark bad release as "prerelease" to de-emphasize
- Create tracking issue for follow-up work

## Post-Rollback Actions

### Immediate (Within 1 hour)
- [ ] **Verify rollback worked**: Test that `update.sh` pulls the correct version
- [ ] **Communicate incident**: 
  - Post in GitHub Discussions if community exists
  - Update any external communication channels
- [ ] **Monitor for issues**: Watch for user reports about the rollback

### Short-term (Within 24 hours)  
- [ ] **Investigate root cause**: Analyze what went wrong in the bad release
- [ ] **Plan fix strategy**: Determine approach for addressing the issue
- [ ] **Create fix branch**: Start work on resolving the underlying problem

### Medium-term (Within 1 week)
- [ ] **Implement fix**: Resolve the issue that caused the rollback
- [ ] **Test thoroughly**: Ensure fix works and doesn't introduce new issues  
- [ ] **Create new release**: Publish patched version
- [ ] **Post-mortem**: Document lessons learned (for major incidents)

## Rollback Limitations

**What rollback CANNOT fix:**
- Database migrations that destroyed data
- Issues requiring manual user intervention
- Problems with user-specific configuration files
- Third-party service integration issues

**In these cases**, additional recovery procedures may be needed beyond the automated rollback.
