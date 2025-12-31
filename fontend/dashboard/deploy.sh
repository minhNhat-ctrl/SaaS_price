#!/bin/bash

# Deploy script for PriceSync Dashboard
# Domain: app.2kvietnam.com

set -e

echo "🚀 Starting deployment..."

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
APP_DIR="/var/www/PriceSynC/Saas_app/fontend/dashboard"
NGINX_CONF="/etc/nginx/sites-available/app.2kvietnam.com"
DOMAIN="app.2kvietnam.com"

# Step 1: Install dependencies
echo -e "${YELLOW}📦 Installing dependencies...${NC}"
cd $APP_DIR
npm install --legacy-peer-deps

# Step 2: Run tests (optional)
# echo -e "${YELLOW}🧪 Running tests...${NC}"
# npm test -- --watchAll=false

# Step 3: Build production
echo -e "${YELLOW}🔨 Building for production...${NC}"
npm run build

# Step 4: Check build output
if [ ! -d "$APP_DIR/build" ]; then
    echo -e "${RED}❌ Build failed! No build directory found.${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Build completed successfully!${NC}"

# Step 5: Setup Nginx
echo -e "${YELLOW}⚙️  Configuring Nginx...${NC}"

# Copy nginx config if not exists
if [ ! -f "$NGINX_CONF" ]; then
    sudo cp $APP_DIR/nginx.conf $NGINX_CONF
    sudo ln -sf $NGINX_CONF /etc/nginx/sites-enabled/app.2kvietnam.com
    echo -e "${GREEN}✅ Nginx configuration created${NC}"
else
    echo -e "${YELLOW}⚠️  Nginx config already exists${NC}"
fi

# Test nginx config
echo -e "${YELLOW}🔍 Testing Nginx configuration...${NC}"
sudo nginx -t

# Step 6: Setup SSL (if not exists)
if [ ! -f "/etc/letsencrypt/live/$DOMAIN/fullchain.pem" ]; then
    echo -e "${YELLOW}🔐 Setting up SSL certificate...${NC}"
    sudo certbot --nginx -d $DOMAIN --non-interactive --agree-tos --email admin@2kvietnam.com
else
    echo -e "${GREEN}✅ SSL certificate already exists${NC}"
fi

# Step 7: Reload Nginx
echo -e "${YELLOW}🔄 Reloading Nginx...${NC}"
sudo systemctl reload nginx

# Step 8: Show status
echo ""
echo -e "${GREEN}✅ Deployment completed successfully!${NC}"
echo ""
echo "📊 Deployment Summary:"
echo "  • Domain: https://$DOMAIN"
echo "  • Build size: $(du -sh $APP_DIR/build | cut -f1)"
echo "  • Files: $(find $APP_DIR/build -type f | wc -l)"
echo ""
echo "🔗 Access your app at: https://$DOMAIN"
echo ""

# Optional: Show logs
echo -e "${YELLOW}📝 Recent Nginx logs:${NC}"
sudo tail -n 5 /var/log/nginx/app.2kvietnam.com.access.log 2>/dev/null || echo "No logs yet"
