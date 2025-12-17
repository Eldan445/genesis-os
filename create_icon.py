from PIL import Image, ImageDraw, ImageFont, ImageFilter

def create_genesis_icon():
    print("🎨 Generating Genesis Icon...")
    
    # 1. Create a blank black canvas (500x500 for high quality)
    size = (500, 500)
    # Background color: Very dark blue/black
    img = Image.new('RGB', size, color=(10, 10, 20))
    draw = ImageDraw.Draw(img)

    # 2. Draw the "G" (Genesis)
    # Since we might not have custom fonts, we draw a geometric G
    
    # Outer Glow Circle (Cyan)
    center = (250, 250)
    radius = 180
    draw.ellipse([center[0]-radius, center[1]-radius, center[0]+radius, center[1]+radius], outline=(0, 242, 255), width=10)
    
    # Inner "DNA" Line (Purple)
    draw.line([(150, 150), (350, 350)], fill=(180, 0, 255), width=20)
    draw.line([(350, 150), (150, 350)], fill=(180, 0, 255), width=20)
    
    # 3. Add a "Neon" Blur effect
    # We make a copy, blur it, and paste the sharp one on top to make it glow
    blurred = img.filter(ImageFilter.GaussianBlur(radius=15))
    final = Image.blend(img, blurred, alpha=0.5)
    
    # Draw the sharp lines again on top for clarity
    draw2 = ImageDraw.Draw(final)
    draw2.ellipse([center[0]-radius, center[1]-radius, center[0]+radius, center[1]+radius], outline=(0, 242, 255), width=5)
    
    # 4. Save
    final.save('genesis_icon.png')
    print("✅ Icon saved as 'genesis_icon.png'")

if __name__ == "__main__":
    create_genesis_icon()