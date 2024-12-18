from flask import Flask, request, jsonify
import logging
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import spacy
import requests
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    filters, 
    ContextTypes, 
    ConversationHandler
)
from fpdf import FPDF
from pdf2image import convert_from_path
import pytesseract
import os
from datetime import datetime
import re

# Initialize Flask
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Download NLTK resources
nltk.download('punkt')
nltk.download('stopwords')

# Load spaCy model
nlp = spacy.load("es_core_news_sm")

def extract_key_points(text, num_points=4):
    """Extracts key points from the text."""
    try:
        doc = nlp(text)
        sentences = list(doc.sents)
        key_sentences = [sent.text.strip() for sent in sentences[:num_points] if len(sent.text.strip()) > 20]
        while len(key_sentences) < num_points:
            key_sentences.append("Información adicional en el texto original")
        return key_sentences
    except Exception as e:
        logger.error(f"Error extracting key points: {str(e)}")
        return ["No se pudieron extraer puntos clave debido a un error."]

def generate_summary(text):
    """Generates a summary of the text."""
    try:
        doc = nlp(text)
        sentences = [sent.text.strip() for sent in doc.sents]
        return " ".join(sentences[:3]) if sentences else "No se pudo generar un resumen."
    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return "No se pudo generar un resumen debido a un error."

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "message": "Server is running"}), 200

@app.route('/documents/analyze', methods=['POST'])
def analyze_document():
    """Analyzes a document."""
    try:
        data = request.json
        if not data or 'content' not in data:
            return jsonify({"error": "No content provided", "message": "Se requiere el campo 'content'"}), 400
        content = data['content']
        section = data.get('section', 'N/A')
        title = data.get('title', 'Sin título')
        summary = generate_summary(content)
        key_points = extract_key_points(content)
        response = {"section": section, "title": title, "summary": summary, "key_points": key_points}
        return jsonify(response), 200
    except Exception as e:
        logger.error(f"Error analyzing document: {str(e)}")
        return jsonify({"error": "Internal server error", "message": str(e)}), 500

# Telegram Bot Code
class DocumentAnalyzerBot:
    def __init__(self):
        self.current_document = None
        self.api_base_url = "http://0.0.0.0:5000"  # Update with Render URL after deployment
        logger.info("Bot initialized")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "¡Bienvenido al Bot de Análisis de Documentos! 👋\n\n" +
            "Sube un documento PDF para comenzar.")
        return 0

    async def handle_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        doc = update.message.document
        if not doc.file_name.endswith('.pdf'):
            await update.message.reply_text("❌ Por favor, sube un documento PDF válido.")
            return 0
        file = await doc.get_file()
        file_path = os.path.join("downloads", doc.file_name)
        os.makedirs("downloads", exist_ok=True)
        await file.download_to_drive(file_path)
        self.current_document = file_path
        await update.message.reply_text("Documento recibido. Analizando...")
        self.analyze_document(file_path, update)
        return 1

    def analyze_document(self, file_path, update):
        try:
            with open(file_path, 'rb') as f:
                text = f.read().decode('utf-8')  # Assuming text PDF
                response = requests.post(
                    f"{self.api_base_url}/documents/analyze",
                    json={"content": text}
                ).json()
                update.message.reply_text(f"Análisis completado: {response}")
        except Exception as e:
            logger.error(f"Error analyzing document: {str(e)}")
            update.message.reply_text("Error al analizar el documento.")

bot = DocumentAnalyzerBot()

# Main function
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
