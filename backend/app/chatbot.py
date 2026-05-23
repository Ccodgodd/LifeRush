import requests
import logging
from backend.app.config import settings

logger = logging.getLogger(__name__)

# Predefined Q&A database for high-fidelity offline/local mode
FAQ_DATABASE = [
    {
        "keywords": ["eligible", "eligibility", "can i donate", "am i fit"],
        "question": "Am I eligible to donate blood?",
        "answer": "To donate blood, you must meet these general guidelines:\n- Be in good general health and feel well.\n- Be at least 18 years old.\n- Weigh at least 110 lbs (50 kg).\n- Have a hemoglobin level of at least 12.5 g/dL.\n- Not have donated blood in the last 56 days.\n- Have a healthy platelet count (>= 150,000 /mcL) and no active infections.\nYou can upload your medical report on the landing page or your profile to let our AI analyze your eligibility instantly!"
    },
    {
        "keywords": ["often", "frequency", "how many times", "interval", "days", "months"],
        "question": "How often can I donate blood?",
        "answer": "The recommended waiting intervals between donations are:\n- **Whole Blood**: Every 56 days (8 weeks) for both men and women.\n- **Platelets**: Every 7 days, up to a maximum of 24 times per year.\n- **Plasma**: Every 28 days (4 weeks).\n- **Double Red Cells**: Every 112 days (16 weeks).\nThese intervals help ensure your body has sufficient time to regenerate red cells and iron stores."
    },
    {
        "keywords": ["food", "diet", "hemoglobin", "increase hb", "iron", "eat", "drink"],
        "question": "What foods increase hemoglobin and iron levels?",
        "answer": "To naturally boost your hemoglobin and iron levels prior to donation, include these foods in your diet:\n- **Iron-Rich Foods**: Red meat, poultry, fish, beans, lentils, spinach, kale, and iron-fortified cereals.\n- **Vitamin C**: Foods rich in Vitamin C (citrus fruits, strawberries, bell peppers, tomatoes) significantly improve iron absorption. Avoid drinking coffee or tea with iron-rich meals, as they hinder iron absorption.\n- **Hydration**: Drink plenty of water (8-10 glasses) on the day before and day of your donation."
    },
    {
        "keywords": ["where", "nearby", "location", "place", "bank", "hospital", "camp", "center"],
        "question": "Where can I donate nearby?",
        "answer": "You can view nearby blood banks, hospitals, and donation camps using our interactive **Nearby Blood Banks Map** on the Donor Dashboard. It uses Google Maps to locate and list active centers in your city, including driving directions and contacts."
    },
    {
        "keywords": ["process", "what happens", "procedure", "steps"],
        "question": "What is the donation process?",
        "answer": "The donation process is simple and takes about 1 hour in total:\n1. **Registration**: Fill out forms with basic identification and details.\n2. **Health Screen**: A brief physical check of temperature, pulse, blood pressure, and hemoglobin.\n3. **Donation**: The actual collection takes only 8-10 minutes (for whole blood).\n4. **Recovery**: Relax in the refreshment area for 10-15 minutes with snacks and fluids."
    },
    {
        "keywords": ["safety", "hurt", "painful", "safe", "disease"],
        "question": "Is blood donation safe? Does it hurt?",
        "answer": "Yes, donating blood is extremely safe. A brand-new, sterile needle is used for every donor and discarded immediately. You cannot contract any disease from donating blood. You will feel a quick, minor pinch when the needle is inserted, but the rest of the process is comfortable."
    }
]

def query_chatbot(user_message: str) -> str:
    """
    Queries OpenAI API if an API key is available, or runs a local keyword matching
    search over the FAQ database to generate answers.
    """
    user_msg_lower = user_message.lower().strip()
    
    # If OpenAI key is set, try using it
    if settings.OPENAI_API_KEY:
        try:
            url = "https://api.openai.com/v1/chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}"
            }
            # Combine offline FAQs as system context for accurate medical guidance
            faq_context = "\n".join([f"Q: {item['question']}\nA: {item['answer']}" for item in FAQ_DATABASE])
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are the LifeRush AI medical assistant. Help blood donors and patients. "
                            "Keep answers clear, highly encouraging, and empathetic. "
                            "Adhere strictly to medical safety regulations. Below is some verified context "
                            "you can reference to answer user questions:\n\n" + faq_context
                        )
                    },
                    {"role": "user", "content": user_message}
                ],
                "temperature": 0.7
            }
            
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code == 200:
                result = response.json()
                return result["choices"][0]["message"]["content"]
            else:
                logger.error(f"OpenAI API returned error: {response.text}")
        except Exception as e:
            logger.error(f"Failed to query OpenAI API: {e}")

    # Local fallback/RAG Mode
    # Perform scoring based on keywords matched in user's query
    best_match = None
    max_matches = 0
    
    for item in FAQ_DATABASE:
        matches = sum(1 for keyword in item["keywords"] if keyword in user_msg_lower)
        if matches > max_matches:
            max_matches = matches
            best_match = item

    if best_match and max_matches > 0:
        return best_match["answer"]

    # General greeting fallbacks
    greetings = ["hi", "hello", "hey", "greetings", "good morning", "good afternoon"]
    if any(greet in user_msg_lower for greet in greetings):
        return (
            "Hello! I am your LifeRush AI Assistant. I can answer your questions about "
            "blood donation eligibility, intervals, diet plans to increase hemoglobin, "
            "or guide you to nearby donation camps. What would you like to know?"
        )
    
    # Generic advice response
    return (
        "I want to make sure I give you accurate information. I can help you with:\n"
        "- Checking if you're eligible to donate (`Am I eligible?`)\n"
        "- Knowing donation intervals (`How often can I donate?`)\n"
        "- Finding foods to increase hemoglobin (`Foods to increase iron`)\n"
        "- Finding nearby blood centers (`Where can I donate nearby?`)\n\n"
        "Feel free to rephrase your query or upload your medical report so I can analyze your metrics!"
    )
