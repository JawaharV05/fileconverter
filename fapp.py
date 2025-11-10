import streamlit as st
import boto3
import time
from io import BytesIO
from botocore.config import Config

# --- AWS CONFIGURATION ---
REGION_NAME = "ap-south-1"   # ✅ Your region
BUCKET_NAME = "file-convo"   # ✅ Your bucket name

# --- READ KEYS SAFELY FROM STREAMLIT SECRETS ---
try:
    AWS_ACCESS_KEY = st.secrets["aws"]["access_key"]
    AWS_SECRET_KEY = st.secrets["aws"]["secret_key"]
except KeyError:
    st.error("❌ AWS credentials not found in Streamlit Secrets!")
    st.stop()

# --- FORCE REGION CONFIG ---
custom_config = Config(
    region_name=REGION_NAME,
    signature_version='s3v4'
)

# --- CONNECT TO S3 ---
try:
    s3_client = boto3.client(
        "s3",
        aws_access_key_id=AWS_ACCESS_KEY,
        aws_secret_access_key=AWS_SECRET_KEY,
        config=custom_config,
        endpoint_url=f"https://s3.{REGION_NAME}.amazonaws.com"
    )
    s3_client.list_buckets()
    st.success("✅ Connected to S3 successfully!")
except Exception as e:
    st.error(f"❌ S3 Connection failed: {e}")
    st.stop()

# --- STREAMLIT UI ---
st.set_page_config(page_title="File Converter", page_icon="⚙️", layout="centered")
st.markdown("<h1 style='text-align: center;'>⚙️ File Converter</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center;'>Upload your file and convert instantly.</p>", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Select a file to convert", type=["csv", "json", "txt", "mp3", "wav"]
)

if uploaded_file:
    file_name = uploaded_file.name
    s3_input_key = f"input1/{file_name}"

    with st.spinner("Uploading your file to S3..."):
        try:
            s3_client.upload_fileobj(uploaded_file, BUCKET_NAME, s3_input_key)
            st.success("✅ File uploaded successfully. Conversion started...")
        except Exception as e:
            st.error(f"❌ Upload failed: {e}")
            st.stop()

    st.info("⏳ Please wait while your file is being converted...")

    output_key_prefix = file_name.rsplit('.', 1)[0]
    found_output = False
    output_key = None

    for i in range(60):  # Wait up to 120 seconds
        st.info(f"🔄 Checking for converted file... ({i+1}/60)")
        response = s3_client.list_objects_v2(Bucket=BUCKET_NAME, Prefix="input1/")
        if "Contents" in response:
            for obj in response["Contents"]:
                if output_key_prefix in obj["Key"] and obj["Key"] != s3_input_key:
                    output_key = obj["Key"]
                    found_output = True
                    break
        if found_output:
            break
        time.sleep(2)

    if found_output:
        st.success(f"🎉 Conversion complete! File ready for download: {output_key.split('/')[-1]}")
        file_obj = s3_client.get_object(Bucket=BUCKET_NAME, Key=output_key)
        file_data = file_obj['Body'].read()

        ext = output_key.split('.')[-1]
        mime_type = {
            'json': 'application/json',
            'csv': 'text/csv',
            'xml': 'application/xml',
            'txt': 'text/plain'
        }.get(ext, 'application/octet-stream')

        st.download_button(
            label="⬇️ Download Converted File",
            data=file_data,
            file_name=output_key.split('/')[-1],
            mime=mime_type
        )
    else:
        st.warning("⚠️ Conversion not finished yet. Try again after a few seconds.")
