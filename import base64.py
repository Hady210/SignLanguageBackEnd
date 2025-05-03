import base64

with open("C:\Users\Ahmed M. AbdElhady\Desktop\4.2\project\problems\1.jpg", "rb") as image_file:
    base64_image = base64.b64encode(image_file.read()).decode('utf-8')
    print(base64_image)