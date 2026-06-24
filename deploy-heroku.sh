#!/bin/bash
set -e
APP_NAME="${1:-petrol-ivanovo}"
echo "Creating Heroku app: $APP_NAME"
heroku create "$APP_NAME" || true
echo "Pushing to Heroku..."
git push heroku main
echo ""
echo "✓ Done!"
echo "Visit: https://$APP_NAME.herokuapp.com"
echo ""
echo "Next: Open https://www.pwabuilder.com"
echo "Load: https://$APP_NAME.herokuapp.com"
echo "Build → Android → Download APK"
