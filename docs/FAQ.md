<img src="../src/hi/static/img/hi-logo-w-tagline-197x96.png" alt="Home Information Logo" width="128">

# Frequently Asked Questions

## Getting Started

### Q: How long does it take to set up?
**A:** Basic installation takes just a few minutes if you have Docker installed. Setting up your first location and adding a few items takes another 15-30 minutes. You can start simple and build up your information over time - there's no need to do everything at once.

### Q: Do I need to be technical to use this?
**A:** The installation requires basic command line usage and Docker, but once it's running, the interface is point-and-click. If you're comfortable installing apps on your computer, you can handle the setup. We're working on making installation even simpler for future versions.

### Q: Can I try it without installing anything?
**A:** Currently, no - Home Information runs locally on your network by design. However, the Docker-based installation is designed to be easily removable if you decide it's not for you. All data is stored in your home directory and can be completely removed by deleting the Docker container and the `~/.hi` directory.

## Data & Privacy

### Q: Where is my data stored?
**A:** All your data stays on your local network. The database file lives in `~/.hi/database/` on your computer, and uploaded files go in `~/.hi/media/`. Nothing is sent to external cloud services unless you explicitly configure integrations that require it.

### Q: What if I want to stop using Home Information?
**A:** Your data is stored in standard formats (SQLite database, regular files) that you can access independently. All uploaded documents remain as normal files on your computer. We're committed to ensuring you're never locked into using our software.

### Q: How do I backup my data?
**A:** Simply backup your `~/.hi` directory - it contains everything. You can also export data through the application interface. We recommend including this directory in your regular backup routine.

### Q: Can multiple people use it simultaneously?
**A:** Yes, Home Information supports multiple users accessing the same installation from different devices on your network. You can optionally enable user authentication if you want separate accounts, or run it in simple mode where anyone on your network can access it.

### Data Portability

### Q: How do I access my data without Home Information?
**A:** All your data lives in standard formats in `~/.hi/`
- **Database**: SQLite database at `~/.hi/database/hi.sqlite3`
  - View with any SQLite tool (DB Browser for SQLite is free)
  - Query with sqlite3 CLI: `sqlite3 ~/.hi/database/hi.sqlite3`
- **Documents**: Regular files in `~/.hi/media/`
- **Backups**: Just copy the entire `~/.hi` directory

We chose SQLite specifically because it's an open format readable by countless tools. Your data is never locked in proprietary
formats.

We also provide some helper scripts [Helper Scripts README](../scripts/README.md).

## Technical Requirements

### Q: What devices can I use to access it?
**A:** Any device with a modern web browser: computers, tablets, smartphones. The interface works especially well on tablets as a dedicated home management display.

### Q: Does it require internet access?
**A:** Core functionality works completely offline. Internet access is only needed for weather data, email alerts, and if you choose to integrate with cloud-based services. The system is designed to gracefully handle internet outages.

### Q: How much storage space does it need?
**A:** The application itself is small. Storage needs depend on how many documents and images you upload. Most users find a few GB is plenty for extensive documentation.

### Q: What about system requirements?
**A:** Very modest. If your computer can run Docker, it can run Home Information. We've tested on systems with as little as 2GB RAM and older processors.

## Integrations & Compatibility

### Q: Do I need Home Assistant, Frigate, HomeBox, etc. to use this?
**A:** No, integrations are completely optional. Home Information provides value as a standalone information management system. Integrations add device control, monitoring, and inventory management capabilities when you want them.

### Q: Will it work with my existing smart home setup?
**A:** If your devices work with Home Assistant, they'll integrate well. Home Assistant supports hundreds of device types and protocols. For security cameras, Frigate and ZoneMinder integrations work with most IP cameras and many older CCTV systems. 

### Q: What if I already have a lot of data in Paperless-ngx, HomeBox, etc.?
**A:** For home inventory tracking, HomeBox items can be connected and displayed on your home layout. Documents from Paperless-ngx and images from Immich can be linked to any item in the Home Information views.

### Q: What if my devices aren't supported?
**A:** You can still use Home Information for documentation and information management about those devices. As the project grows, we'll add more integrations based on user demand.

### Q: Can I use it with cloud-based home automation?
**A:** The philosophy of Home Information aligns best with local-control systems and we have focused on integrations with similar philsophies. Cloud-based integrations may be added if there is demand, but would require additional development.

## Comparison with Alternatives

### Q: How is this different from just using a note-taking app?
**A:** The spatial, visual organization makes information much easier to find and manage. Instead of searching through lists or folders, you click where something is located. Plus, device integration means you can control things and see status information alongside documentation.

### Q: Why not just use Home Assistant directly?
**A:** Home Assistant is excellent for device control but wasn't designed for information management. Home Information complements Home Assistant by providing the spatial organization and document management that makes device control more meaningful.

### Q: How does this compare to property management software?
**A:** Most property management tools are designed for landlords managing multiple properties, not homeowners managing their own home. Home Information focuses on the day-to-day information needs of people living in their space with s special focus on spatial organization of that data.

## Future Development

### Q: What integrations are planned next?
**A:** We're guided by user demand and we have a few candidates on our roadmap. The integration architecture makes adding new systems straightforward.

### Q: Will there be a mobile app?
**A:** The web interface works well on mobile devices, but we're considering a dedicated mobile app for quick access and notifications when away from home.

### Q: How can I influence development priorities?
**A:** Join the community! Use the software, report issues, request features, and contribute to discussions. We're especially interested in hearing about real-world use cases and pain points.

## Troubleshooting

### Q: The installation failed. What should I check?
**A:** Most installation issues relate to Docker setup or system permissions. Check that Docker is running, you have sufficient disk space, and your user account has permissions to create files in your home directory. See the [Installation Guide](Installation.md) troubleshooting section for specific error messages.

### Q: My data is in `~/home-information` instead of `~/.hi` — is that right?
**A:** Yes. Home Information normally stores everything in the hidden `~/.hi` directory. However, **snap-packaged Docker** (and some other confined Docker setups) cannot read files inside hidden ("dot") directories, which makes the install fail with a `permission denied` error. When the installer detects this, it uses the visible `~/home-information` directory instead. Everything works the same — just substitute `~/home-information` for `~/.hi` in any instructions (your data lives in `~/home-information/database/` and `~/home-information/media/`). If you'd prefer the hidden `~/.hi` default, install Docker from the official apt/yum repository instead of the snap.

### Q: Can I access it from outside my home network?
**A:** Yes, but it requires additional network configuration (port forwarding, dynamic DNS, etc.). For security reasons, we recommend using VPN access to your home network rather than exposing the service directly to the internet.

### Q: The interface seems slow. How can I improve performance?
**A:** Performance is typically excellent on local networks. Slowness usually indicates network issues or insufficient system resources. Try accessing from the same machine where it's running to isolate network vs. system performance issues.

### Q: How do I get help if I'm stuck?
**A:** Check the documentation first, then create an issue on the GitHub repository with details about your setup and the specific problem you're encountering. The community is generally helpful with troubleshooting.

## Project & Community

### Q: Is this project actively maintained?
**A:** Yes, we're actively developing and maintaining Home Information. We're currently focused on stabilizing the core functionality and improving the user experience based on early adopter feedback.

### Q: Can I contribute without being a programmer?
**A:** Absolutely! We need help with documentation, testing, user experience design, and community building. Using the software and providing feedback is valuable contribution.

### Q: What's the long-term vision?
**A:** To create the missing piece that makes home technology actually useful for managing daily life. We want to bridge the gap between device-centric automation and people-centric information management.

### Q: Is it really free?
**A:** Yes, Home Information is open source software released under the MIT license for personal use. You can use it freely, modify it, and even redistribute it. There are no subscription fees or premium tiers.
