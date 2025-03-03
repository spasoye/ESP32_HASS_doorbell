import asyncio
from camera import Camera, FrameSize, PixelFormat

cam = Camera(frame_size=FrameSize.VGA, pixel_format=PixelFormat.JPEG, jpeg_quality=85, init=False)
html = None

# TODO: research more about asyncio
async def stream_camera(writer):
    
    try:
        cam.init()
        if not cam.get_bmp_out() and cam.get_pixel_format() != PixelFormat.JPEG:
            cam.set_bmp_out(True)

        writer.write(b'HTTP/1.1 200 OK\r\nContent-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n')
        await writer.drain()

        while True:
            frame = cam.capture()
            if frame:
                if cam.get_pixel_format() == PixelFormat.JPEG:
                    writer.write(b'--frame\r\nContent-Type: image/jpeg\r\n\r\n')
                else:
                    writer.write(b'--frame\r\nContent-Type: image/bmp\r\n\r\n')
                writer.write(frame)
                await writer.drain()
    finally:
        cam.deinit()
        writer.close()
        await writer.wait_closed()
        print("Streaming stopped and camera deinitialized.")

async def handle_client(reader, writer):
    try:
        request = await reader.read(1024)
        request = request.decode()

        if 'GET /stream' in request:
            print("Start streaming...")
            await stream_camera(writer)

        elif 'GET /set_' in request:
            method_name = request.split('GET /set_')[1].split('?')[0]
            value = int(request.split('value=')[1].split(' ')[0])
            set_method = getattr(cam, f'set_{method_name}', None)
            if callable(set_method):
                print(f"Setting {method_name} to {value}")
                set_method(value)
                response = 'HTTP/1.1 200 OK\r\n\r\n'
                writer.write(response.encode())
                await writer.drain()
            else:
                response = 'HTTP/1.1 404 Not Found\r\n\r\n'
                writer.write(response.encode())
                await writer.drain()

        elif 'GET /get_' in request:
            method_name = request.split('GET /get_')[1].split(' ')[0]
            get_method = getattr(cam, f'get_{method_name}', None)
            if callable(get_method):
                value = get_method()
                print(f"{method_name} is {value}")
                response = f'HTTP/1.1 200 OK\r\n\r\n{value}'
                writer.write(response.encode())
                await writer.drain()
            else:
                response = 'HTTP/1.1 404 Not Found\r\n\r\n'
                writer.write(response.encode())
                await writer.drain()

        else:
            global html
            writer.write('HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n'.encode())
            writer.write(html.encode())
            await writer.drain()
    except Exception as e:
        print(f"Error: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def start_server(ip, port=80):
    try:
        with open("CameraSettings.html", 'r') as file:
            global html
            html = file.read()
    except Exception as e:
        print("Error reading CameraSettings.html file. You might forgot to copy it from the examples folder.")
        raise e

    server = await asyncio.start_server(handle_client, ip, port)
    print(f"Server is running on {ip}:{port}")
    while True:
        await asyncio.sleep(3600)

