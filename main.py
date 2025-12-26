from fastapi import FastAPI, HTTPException, File, UploadFile
from pydantic import BaseModel
from supabase import create_client, Client
from fastapi.middleware.cors import CORSMiddleware
import time

app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ใน Production ควรเปลี่ยน * เป็น "http://localhost:5173"
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ---------------------------------------------------------
# 1. ตั้งค่า Supabase (ใส่ URL และ Key ของคุณที่นี่)
# ---------------------------------------------------------
SUPABASE_URL = "https://ldarzpdiedgznolqcdvh.supabase.co"
SUPABASE_KEY = "sb_publishable_XiSdQlNdD6s_0ryroJq1IA_SgsHLQ_w"

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---------------------------------------------------------
# 2. สร้าง Model รองรับข้อมูล (Schema)
# ---------------------------------------------------------

# สำหรับ Login (ใช้แค่เมลกับรหัส)
class UserLoginSchema(BaseModel):
    email: str
    password: str

# สำหรับ Signup (เพิ่มเบอร์โทรศัพท์)
class UserSignupSchema(BaseModel):
    email: str
    password: str
    phone: str

# ---------------------------------------------------------
# 3. API เดิมของคุณ
# ---------------------------------------------------------
@app.get("/")
def read_root():
    return {"message": "Hello World", "status": "OK"}

@app.get("/item/{item_id}")
def read_item(item_id: int):
    return {"item_id": item_id, "name": "ตัวอย่างสินค้า"}

# ---------------------------------------------------------
# 4. API ใหม่: สมัครสมาชิก (Signup) เก็บเบอร์โทร
# ---------------------------------------------------------
@app.post("/signup")
def sign_up(user: UserSignupSchema):
    try:
        # ส่งข้อมูลไป Supabase
        # เราเก็บเบอร์โทร (phone) ไว้ในส่วน data (User Metadata)
        response = supabase.auth.sign_up({
            "email": user.email, 
            "password": user.password,
            "options": {
                "data": {
                    "phone": user.phone
                }
            }
        })
        return {"message": "สมัครสมาชิกสำเร็จ", "data": response}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---------------------------------------------------------
# 5. API ใหม่: เข้าสู่ระบบ (Login)
# ---------------------------------------------------------
@app.post("/login")
def login(user: UserLoginSchema):
    try:
        response = supabase.auth.sign_in_with_password({
            "email": user.email, 
            "password": user.password
        })
        
        # ดึงเบอร์โทรที่เคยบันทึกไว้ออกมาโชว์ตอน Login สำเร็จ
        user_phone = response.user.user_metadata.get('phone', 'ไม่ระบุ')

        return {
            "message": "เข้าสู่ระบบสำเร็จ",
            "access_token": response.session.access_token,
            "user_info": {
                "id": response.user.id,
                "email": response.user.email,
                "phone": user_phone
            }
        }
    except Exception as e:
        raise HTTPException(status_code=401, detail="อีเมลหรือรหัสผ่านไม่ถูกต้อง")
    
@app.post("/upload-image")
async def upload_image(file: UploadFile = File(...)):
    try:
        # 1. ตั้งชื่อไฟล์ไม่ให้ซ้ำ
        file_ext = file.filename.split(".")[-1]
        file_name = f"{int(time.time())}.{file_ext}"
        
        # 2. ส่งขึ้น Supabase Storage (อย่าลืมสร้าง Bucket ชื่อ 'chat-images' และเปิด Public)
        bucket_name = "chat-images"
        file_content = await file.read()
        
        supabase.storage.from_(bucket_name).upload(
            path=file_name,
            file=file_content,
            file_options={"content-type": file.content_type}
        )
        
        # 3. ขอ Link รูปที่เป็น Public กลับไป
        public_url = supabase.storage.from_(bucket_name).get_public_url(file_name)
        
        return {"url": public_url}
        
    except Exception as e:
        print("Upload Error:", e)
        raise HTTPException(status_code=500, detail="อัปโหลดรูปไม่สำเร็จ")