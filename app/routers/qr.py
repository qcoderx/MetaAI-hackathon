from fastapi import APIRouter, HTTPException
import httpx
import os
import asyncio

router = APIRouter(prefix="/qr", tags=["QR Code"])

@router.get("/generate/{instance_name}")
async def generate_qr_code(instance_name: str):
    """Force generate QR code for WhatsApp connection"""
    try:
        evolution_base_url = os.getenv('EVOLUTION_API_URL', 'http://localhost:8081')
        evolution_api_key = os.getenv('EVOLUTION_API_KEY', '74BDBE32-21C5-44F9-B084-8844C749EEC5')
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Method 1: Try to restart the instance
            restart_response = await client.put(
                f"{evolution_base_url}/instance/restart/{instance_name}",
                headers={"apikey": evolution_api_key}
            )
            print(f"Restart response: {restart_response.status_code}")
            
            # Wait for restart
            await asyncio.sleep(3)
            
            # Method 2: Try to connect
            connect_response = await client.get(
                f"{evolution_base_url}/instance/connect/{instance_name}",
                headers={"apikey": evolution_api_key}
            )
            print(f"Connect response: {connect_response.status_code}")
            
            if connect_response.status_code == 200:
                connect_data = connect_response.json()
                qr_code = connect_data.get("base64", "")
                if qr_code:
                    return {
                        "instance_name": instance_name,
                        "qr_code": qr_code,
                        "status": "ready_to_scan",
                        "method": "connect_endpoint"
                    }
            
            # Method 3: Check instance status
            status_response = await client.get(
                f"{evolution_base_url}/instance/status/{instance_name}",
                headers={"apikey": evolution_api_key}
            )
            
            if status_response.status_code == 200:
                status_data = status_response.json()
                print(f"Status data: {status_data}")
                
                # Look for QR code in status
                if "qrcode" in status_data:
                    qr_data = status_data["qrcode"]
                    if isinstance(qr_data, dict) and "base64" in qr_data:
                        return {
                            "instance_name": instance_name,
                            "qr_code": qr_data["base64"],
                            "status": "ready_to_scan",
                            "method": "status_endpoint"
                        }
            
            # Method 4: Create a new QR code by reconnecting
            reconnect_payload = {"qrcode": True}
            reconnect_response = await client.post(
                f"{evolution_base_url}/instance/connect/{instance_name}",
                json=reconnect_payload,
                headers={"apikey": evolution_api_key}
            )
            
            print(f"Reconnect response: {reconnect_response.status_code}")
            
            if reconnect_response.status_code in [200, 201]:
                reconnect_data = reconnect_response.json()
                qr_code = reconnect_data.get("base64", "")
                if qr_code:
                    return {
                        "instance_name": instance_name,
                        "qr_code": qr_code,
                        "status": "ready_to_scan",
                        "method": "reconnect_endpoint"
                    }
            
            return {
                "instance_name": instance_name,
                "qr_code": "",
                "status": "failed",
                "message": "Could not generate QR code. Instance may need manual intervention.",
                "debug": {
                    "restart_status": restart_response.status_code,
                    "connect_status": connect_response.status_code,
                    "status_status": status_response.status_code if 'status_response' in locals() else "not_tried",
                    "reconnect_status": reconnect_response.status_code if 'reconnect_response' in locals() else "not_tried"
                }
            }
            
    except Exception as e:
        return {
            "instance_name": instance_name,
            "qr_code": "",
            "status": "error",
            "message": str(e)
        }

@router.delete("/cleanup/{instance_name}")
async def cleanup_instance(instance_name: str):
    """Delete and recreate instance to force QR generation"""
    try:
        evolution_base_url = os.getenv('EVOLUTION_API_URL', 'http://localhost:8081')
        evolution_api_key = os.getenv('EVOLUTION_API_KEY', '74BDBE32-21C5-44F9-B084-8844C749EEC5')
        base_url = os.getenv('BASE_URL', 'http://localhost:8000')
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Delete the instance
            delete_response = await client.delete(
                f"{evolution_base_url}/instance/delete/{instance_name}",
                headers={"apikey": evolution_api_key}
            )
            
            print(f"Delete response: {delete_response.status_code}")
            
            # Wait for deletion
            await asyncio.sleep(2)
            
            # Recreate the instance
            payload = {
                "instanceName": instance_name,
                "qrcode": True,
                "integration": "WHATSAPP-BAILEYS",
                "webhook": {
                    "url": f"{base_url}/webhooks/whatsapp/{instance_name}",
                    "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"]
                }
            }
            
            create_response = await client.post(
                f"{evolution_base_url}/instance/create",
                json=payload,
                headers={"apikey": evolution_api_key}
            )
            
            print(f"Create response: {create_response.status_code}")
            
            if create_response.status_code in [200, 201]:
                # Wait for initialization
                await asyncio.sleep(3)
                
                # Try to get QR code
                connect_response = await client.get(
                    f"{evolution_base_url}/instance/connect/{instance_name}",
                    headers={"apikey": evolution_api_key}
                )
                
                if connect_response.status_code == 200:
                    connect_data = connect_response.json()
                    qr_code = connect_data.get("base64", "")
                    
                    return {
                        "instance_name": instance_name,
                        "action": "recreated",
                        "qr_code": qr_code,
                        "status": "ready_to_scan" if qr_code else "generating"
                    }
            
            return {
                "instance_name": instance_name,
                "action": "failed",
                "message": f"Failed to recreate instance. Status: {create_response.status_code}"
            }
            
    except Exception as e:
        return {
            "instance_name": instance_name,
            "action": "error",
            "message": str(e)
        }