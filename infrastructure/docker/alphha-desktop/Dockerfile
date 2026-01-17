# Alphha Security Desktop
# Based on linuxserver/webtop with custom branding and security tools
FROM linuxserver/webtop:debian-xfce

LABEL maintainer="CyberAIx <support@cyyberaix.in>"
LABEL description="Alphha Security Desktop - Web-accessible security research environment"

# Install security tools and utilities
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl wget git vim nano htop tree unzip \
    net-tools iputils-ping traceroute nmap netcat-openbsd dnsutils tcpdump \
    python3 python3-pip python3-venv \
    build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /usr/share/backgrounds/alphha /etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml

# Copy wallpaper and logo
COPY wallpaper.png /usr/share/backgrounds/alphha/wallpaper.png
COPY alphha-logo.png /usr/share/pixmaps/alphha-logo.png

# Configure XFCE desktop wallpaper
RUN echo '<?xml version="1.0" encoding="UTF-8"?>\n\
<channel name="xfce4-desktop" version="1.0">\n\
  <property name="backdrop" type="empty">\n\
    <property name="screen0" type="empty">\n\
      <property name="monitorscreen" type="empty">\n\
        <property name="workspace0" type="empty">\n\
          <property name="color-style" type="int" value="0"/>\n\
          <property name="image-style" type="int" value="5"/>\n\
          <property name="last-image" type="string" value="/usr/share/backgrounds/alphha/wallpaper.png"/>\n\
        </property>\n\
      </property>\n\
    </property>\n\
  </property>\n\
</channel>' > /etc/skel/.config/xfce4/xfconf/xfce-perchannel-xml/xfce4-desktop.xml

# Create welcome script
RUN echo '#!/bin/bash\n\
clear\n\
echo ""\n\
echo "    _    _       _     _           "\n\
echo "   / \\  | |_ __ | |__ | |__   __ _ "\n\
echo "  / _ \\ | |  _ \\|  _ \\|  _ \\ / _  |"\n\
echo " / ___ \\| | |_) | | | | | | | (_| |"\n\
echo "/_/   \\_\\_| .__/|_| |_|_| |_|\\__,_|"\n\
echo "          |_|                       "\n\
echo ""\n\
echo "  Security Research Environment"\n\
echo "  Powered by CyberAIx"\n\
echo ""\n\
echo "Available Tools: nmap, tcpdump, netcat, python3"\n\
echo ""' > /usr/local/bin/alphha-welcome && chmod +x /usr/local/bin/alphha-welcome

# Create custom bashrc
RUN echo 'export PS1="\\[\\033[01;32m\\]\\u@alphha\\[\\033[00m\\]:\\[\\033[01;34m\\]\\w\\[\\033[00m\\]\\$ "\n\
if [ -z "$ALPHHA_WELCOMED" ]; then\n\
    export ALPHHA_WELCOMED=1\n\
    /usr/local/bin/alphha-welcome\n\
fi\n\
alias ll="ls -la"\n\
alias la="ls -A"' > /etc/skel/.bashrc

# Replace Selkies branding with Alphha
RUN find /opt -name "*.html" -exec sed -i 's/Selkies/Alphha/g' {} \; 2>/dev/null || true && \
    find /opt -name "*.js" -exec sed -i 's/Selkies/Alphha/g' {} \; 2>/dev/null || true && \
    find /opt -name "*.html" -exec sed -i 's|https://github.com/selkies-project/selkies-gstreamer||g' {} \; 2>/dev/null || true

# Rename Thunar desktop entry to Files
RUN if [ -f /usr/share/applications/thunar.desktop ]; then \
    sed -i 's/^Name=Thunar.*/Name=Files/' /usr/share/applications/thunar.desktop && \
    sed -i 's/^Name\[.*\]=.*//' /usr/share/applications/thunar.desktop; \
    fi

# Set environment
ENV TITLE="Alphha Desktop"
ENV PUID=1000
ENV PGID=1000

EXPOSE 3000
