from openai import OpenAI
from gtts import gTTS
from io import BytesIO
import streamlit as st
from streamlit_searchbox import st_searchbox
import base64
import requests
import json
import redis
import re

# Set page config to wide mode
st.set_page_config(layout="wide")

# Initialize OpenAI client
client = OpenAI()


# Connect to Redis instance
r = redis.Redis(host=st.secrets["REDIS_HOST"], port=st.secrets["REDIS_PORT"], password=st.secrets["REDIS_PASSWORD"], decode_responses=True)

# Instruction paragraph with FontAwesome CSS included
st.markdown(
    """
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.1/css/all.min.css">
    <div style="display:flex;align-items:center">
        <i class="fas fa-search" style="font-size:48px; margin-right: 10px;"></i>
        <div>
            <h3>Discover Product Insights</h3>
            <p>This app uses AI to provide detailed information and insights about various products.</p>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)

 # UI for selecting input method
input_method = st.radio("Select Input Method", ("Search Box", "File Upload", "Camera Capture"))

# Define the function for getting search suggestions with extra flexibility
def get_search_suggestions(query, **kwargs):
    try:
        # Add '/complete/' and 'client' parameter to the search URL
        url = f"http://google.com/complete/search?client=chrome&q={query}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.102 Safari/537.36 Edge/18.19582"
        }
        response = requests.get(url, headers=headers)
        results = json.loads(response.text)[1]

        # Insert the user input as the first option
        results.insert(0, query)

        return results
    except Exception as e:
        print(e)
        return []

# Function to retrieve ingredients and analysis from OpenAI
def get_analysis(product_name):
    key = f'review:{product_name}'
    result = r.get(key)
    if result is not None:
        return result
    else:
        prompt = f"""As a popular, witty British product reviewer, write a comprehensive review on {product_name}. The review should adapt to the specific type of product, focusing on features, benefits, potential drawbacks, and alternative options that are relevant. Each section should be substantial, utilizing narrative text, bullet points, and tables where appropriate. Make sure your 2000 tokens are well spent:

1. **Summary**
   - **Overview & Review**: Provide a thorough review discussing the main features, benefits, and market appeal of the product. Be critical and include anecdotes or comparisons to bring the review to life. Use customer and professional sources of feedback. Use the following rating scale to give a star rating and explain why, with clear reasoning and wit. When giving more or less than 3 stars don't do so without significant justification and reasoning. It's very important the user understands why the rating was given. If the product is older, be sure to mention how it was for its era:

Rating Scale:
1 Star ⭐️: Poor - Significant issues, fails to meet basic expectations.
2 Stars ⭐️⭐️: Fair - Limited functionality, several problems.
3 Stars ⭐️⭐️⭐️: Good - Meets basic expectations with some minor drawbacks.
4 Stars ⭐️⭐️⭐️⭐️: Very Good - Exceeds expectations with minimal issues.
5 Stars ⭐️⭐️⭐️⭐️⭐️: Excellent - Exceptional performance, top-tier features.

2. **Feature Analysis**
   - **Table**: Rate key features crucial to the product's category. For example, assess battery life and camera quality for smartphones, insulation and durability for clothing, energy efficiency for appliances, or precision and ergonomics for tools. Provide detailed explanations for each rating, including performance metrics and user experience insights.

3. **Specifications**
   - **Table**: List specifications crucial to understanding the product's performance and quality. Tailor this section to fit the product, such as detailing tech specs for electronics, fabric composition for clothing, or capacity and power settings for appliances. Include a narrative explanation of how these specs compare to industry standards.

4. **Safety and Compliance**
   - **Table**: Detail any safety features, potential concerns, and compliance with regulations relevant to the product type. Analyze how these measures compare to competitors.

5. **Cost Assessment**
   - Discuss the purchase cost, value for money, and any ongoing expenses relevant to the product type, such as maintenance costs for vehicles or appliances, or care instructions for clothing.

6. **Maintenance**
   - Outline the recommended maintenance schedule and detail common issues and solutions, suitable for the product category.

7. **Comparable Products**
   - **Table**: Compare this product with at least three similar items within the same category. Discuss strengths and weaknesses in detail, focusing on performance and value.

8. **Issues and Cautions**
   - Elaborate on common problems associated with the product type and warning signs that users should be aware of.

9. **Unique Aspects**
   - List and explain any fun facts, hidden features, or unique quirks of the product, showcasing why it might stand out in its category.

10. **Recommendations**
   - Provide recommendations on the best configurations or versions to purchase, or suggest alternative products that offer better value or performance.

11. **Sources**
   - Include a list of reviews and clickable links for detailed exploration of {product_name}.

This review should be rich with detail and context, using clear, engaging language that reflects the style of a seasoned reviewer and adapts to the specific needs and nuances of the product type."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": product_name}
            ],
            max_tokens=4096,
        )
        analysis = response.choices[0].message.content.strip()
        r.set(key, analysis)
        return analysis

def clean_text_for_tts(text):
    # Remove or replace markdown and special characters
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)  # Remove bold markdown
    text = re.sub(r'\#\#(.*?)\n', r'\1. ', text)  # Translate headers to plain text
    text = re.sub(r'\#(.*?)\n', r'\1. ', text)  # Ensure single hashes are also replaced
    text = re.sub(r'\* (.*?)\n', r'\1. ', text)  # Translate markdown list items
    text = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', text)  # Remove markdown links, keeping link text
    text = re.sub(r'⭐️', 'star ', text)  # Replace star emojis with word "star"
    text = text.replace('|', ', ').replace('-', ' ').replace('`', '')  # Remove or replace other special characters
    return text



def display_analysis(analysis, mute_audio=True):
    st.subheader("AI Analysis:")
    st.write(analysis)  # Display the original analysis text

    if not mute_audio:
        clean_analysis = clean_text_for_tts(analysis)  # Clean the text only for TTS
        audio_stream = BytesIO()
        tts = gTTS(text=clean_analysis, lang='en')  # Use the cleaned text for generating speech
        tts.write_to_fp(audio_stream)
        st.audio(audio_stream, format="audio/mpeg", start_time=0)

# Search Box/Input Method
if input_method == "Search Box":
    st.title("Review Products")
    # Instruction for using the search box
    st.markdown("""
    Instructions for Search Box:
    Instructions for Search Box:
    - Enter the product name, brand, or model in the search box.
    - Select it from the drop-down menu.
    - Click "Search" to start the analysis.
    """)
    product_name = st_searchbox(
        search_function=get_search_suggestions,
        placeholder="e.g., Samsung Galaxy S21 Smartphone",
        label=None,
        clear_on_submit=False,
        clearable=True,
        key="product_search",
    )
    search_button = st.button("Search")
    mute_audio = st.checkbox("Reset & Don't Load Audio", value=True)
    if search_button:
        with st.spinner("Analyzing..."):
            analysis = get_analysis(product_name)
        display_analysis(analysis)

# File Upload/Input Method
elif input_method == "File Upload":
    st.title("Upload Product Image")
    # Instruction for uploading files
    st.markdown("""
    Instructions for File Upload:
   - Click 'Upload an Image' to select an image file from your device.
    - Supported formats are JPG and PNG.
    - The app will analyze the image and extract product details for further analysis.
    """)
    uploaded_image = st.file_uploader("Upload an image", type=['jpg', 'png'])
    
    if uploaded_image:
        with st.spinner("Processing..."):
            # Read image bytes
            image_bytes = uploaded_image.read()
            # Encode image to base64
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            
            # Display the uploaded image with smaller size
            st.image(image_bytes, caption='Uploaded Image', width=300)
            
            # Define user message content
            user_message_content = {
                "type": "text",
                "text": """Reply with only the product name, specification and product type if available. Example: Samsung Galaxy S22 Ultra Smartphone, or Super Mario Brothers Nintendo Gameboy Game"""
            }
            
            # Send image and user message to OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [user_message_content,
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{image_b64}",
                                        },
                                    },
                                   ],
                    }
                ],
                max_tokens=50,
            )
            # Get the analysis from the response
            product_name = response.choices[0].message.content
            
            # Display the analysis
            st.write("Product:")
            st.write(product_name)
            
            analysis = get_analysis(product_name)
            display_analysis(analysis) 

    
elif input_method == "Camera Capture":
    # Camera Capture Functionality
    st.title("Capture Image with Camera")
    # Instruction for using the camera
    st.markdown("""
    Instructions for Camera Capture:
    - Snap a photo of the product.
    - Ensure the picture is clear to optimize analysis accuracy.
    - The app will process the captured image to identify the product.
    """)
    captured_image = st.camera_input("Capture an image")
    
    if captured_image:
        with st.spinner("Processing..."):
            # Read image bytes
            image_bytes = captured_image.read()
            # Encode image to base64
            image_b64 = base64.b64encode(image_bytes).decode("utf-8")
            
            # Display the captured image with smaller size
            #st.image(image_bytes, caption='Captured Image', width=300)
            
            # Define user message content
            user_message_content = {
                "type": "text",
                "text": """Reply with only the product name, specification and product type if available. Example: Samsung Galaxy S22 Ultra Smartphone, or Super Mario Brothers Nintendo Gameboy Game"""
            }
            
            # Send image and user message to OpenAI API
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": [user_message_content,
                                    {
                                        "type": "image_url",
                                        "image_url": {
                                            "url": f"data:image/jpeg;base64,{image_b64}",
                                        },
                                    },
                                   ],
                    }
                ],
                max_tokens=50,
            )
            
            # Get the analysis from the response
            product_name = response.choices[0].message.content
            
            # Display the analysis
            st.write("Product:")
            st.write(product_name)

            analysis = get_analysis(product_name)
            display_analysis(analysis) 
st.markdown(
    """
    <style>
    table {
        width: 100%;
        margin-left: auto;
        margin-right: auto;
        text-align: center;
    }
    th, td {
        padding: 8px;
        border-bottom: 1px solid #ddd;
    }
    </style>
    <table>
        <tr>
            <th>1 Star ⭐️</th>
            <th>2 Stars ⭐️⭐️</th>
            <th>3 Stars ⭐️⭐️⭐️</th>
            <th>4 Stars ⭐️⭐️⭐️⭐️</th>
            <th>5 Stars ⭐️⭐️⭐️⭐️⭐️</th>
        </tr>
        <tr>
            <td>Poor - Does not meet expectations, significant issues.</td>
            <td>Fair - Some functionality but with many problems.</td>
            <td>Good - Meets expectations with average performance and minor drawbacks.</td>
            <td>Very Good - Exceeds expectations, offering superior functionality with very few issues.</td>
            <td>Excellent - Exceptional performance with state-of-the-art features.</td>
        </tr>
    </table>
    """,
    unsafe_allow_html=True
)

st.divider()
expander = st.expander("Legal and Data Privacy Statement", expanded=False)
with expander:
    st.markdown(
    """
<p style="font-size:14px;">Legal Statement</p>
<p style="font-size:14px;">
This application ("App") is provided "as is" without any warranties, express or implied. The information provided by the App is intended to be used for informational purposes only and not as a substitute for professional advice, diagnosis, or treatment. Always seek the advice of your qualified info provider with any questions you may have regarding a product. Never disregard professional advice or delay in seeking it because of something you have read on the App.
</p>
<p style="font-size:14px;">
The App uses the OpenAI Application Protocol Interface (API) to analyze  products and provide an assessment. This information is not intended to be exhaustive and does not cover all possible uses, directions, precautions, or adverse effects that may occur. While we strive to provide accurate information, we make no representation and assume no responsibility for the accuracy of information on or available through the App.
</p>
<p style="font-size:14px;">
The App does not endorse any specific product, service, or treatment. The use of any information provided by the App is solely at your own risk. The App and its owners or operators are not liable for any direct, indirect, punitive, incidental, special or consequential damages that result from the use of, or inability to use, this site.
</p>
<p style="font-size:14px;">
Certain state laws do not allow limitations on implied warranties or the exclusion or limitation of certain damages. If these laws apply to you, some or all of the above disclaimers, exclusions, or limitations may not apply to you, and you might have additional rights.
</p>
<p style="font-size:14px;">
By using this App, you agree to abide by the terms of this legal statement.
</p>
<p style="font-size:14px;">
* This information is based on provided references sourced by AI. It should not be taken as medical advice.
</p>
<p style="font-size:14px;">Data Privacy Statement</p>
<p style="font-size:14px;">
This application ("App") respects your privacy. This statement outlines our practices regarding your data.
</p>
<p style="font-size:14px;">
<b>Information Collection:</b> The only data the App collects is the product name queries you enter when you use the App. We do not collect any personal data, including contact information.
</p>
<p style="font-size:14px;">
<b>Information Usage:</b> Your product name queries are used solely to provide the App's services, specifically to analyze product ingredients and offer health-related information. We now cache the results of previously searched items to speed up the performance of the App. All data is processed in real time and is not stored on our servers or databases beyond this purpose.
</p>
<p style="font-size:14px;">
<b>Information Sharing:</b> We do not share your data with any third parties, except as necessary to provide the App's services, such as interacting with the OpenAI API.
</p>
<p style="font-size:14px;">
<b>User Rights:</b> As we do not store your data beyond the current session, we cannot facilitate requests for data access, correction, or deletion.
</p>
<p style="font-size:14px;">
<b>Security Measures:</b> We implement security measures to protect your data during transmission, but no system is completely secure. We cannot fully eliminate the risks associated with data transmission.
</p>
<p style="font-size:14px;">
<b>Changes to this Policy:</b> Any changes to this data privacy statement will be updated on the App.
</p>
<p style="font-size:14px;">
<b>Ownership of Data:</b> All output data generated by the App, including but not limited to the analysis of product ingredients, belongs to the owner of the App. The owner retains the right to use, reproduce, distribute, display, and perform the data in any manner and for any purpose. The user acknowledges and agrees that any information input into the App may be used in this way, subject to the limitations set out in the Data Privacy Statement.
</p>

    """,
    unsafe_allow_html=True,
)
