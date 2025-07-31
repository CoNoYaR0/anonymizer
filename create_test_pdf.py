from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_test_cv(filename="test_cv.pdf"):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter

    c.drawString(72, height - 72, "Nom: Jean Dupont")
    c.drawString(72, height - 92, "Email: jean.dupont@example.com")
    c.drawString(72, height - 112, "Téléphone: 01-23-45-67-89")
    c.drawString(72, height - 132, "Adresse: 123 Rue de Paris, 75001 Paris")
    c.drawString(72, height - 172, "Compétences: Python, FastAPI, Docker")
    c.drawString(72, height - 212, "Expérience: Développeur chez TechCorp de 2020 à 2023.")

    c.save()
    print(f"'{filename}' created successfully.")

if __name__ == "__main__":
    create_test_cv()
