import json
import os
import socket
import threading
import math

import pygame
import sys

import map_maker
from map_maker import MapMaker

font_cache = {}


def get_font(name, size):
    if name not in font_cache:
        font_cache[name] = {}

    size_cache = font_cache[name]
    if size not in size_cache:
        f = pygame.font.Font(name, size)
        size_cache[size] = (pygame.font.Font(name, size), f.render("0", False, (0, 0, 0)).get_size())

    return size_cache[size]


def calculate_ratio(img, w, h):
    if w and h:
        y_ratio = h / img.get_height()
        x_ratio = w / img.get_width()

        return min(y_ratio, x_ratio)
    elif w:
        return w / img.get_width()
    elif h:
        return h / img.get_height()
    else:
        return 1.0


def scale_image(img, ratio):
    return pygame.transform.scale(img, (round(img.get_width() * ratio), round(img.get_height() * ratio)))


def blit_monospace(surface, rect, font, txt, color):
    font, size = font
    x = rect.centerx - len(txt) * (size[0] // 2)
    y = rect.centery - size[1] // 2

    for a in txt:
        rendered = font.render(a, False, color)
        surface.blit(rendered, (x + round(size[0] / 2 - rendered.get_size()[0] / 2), y))
        x += size[0]


class Meter(object):
    def __init__(self, geometry, frame_color, bg_color, warn_color, txt_color):
        super().__init__()
        self.frame_color = frame_color
        self.bg_color = bg_color

        self.txt_color = txt_color
        self.warn_color = warn_color

        self.rect = pygame.Rect(*geometry)


class AngleMeter(Meter):
    def __init__(self, image_file, geometry, frame_color=(0x98, 0x6c, 0x6a), bg_color=(0x78, 0x4f, 0x41),
                 warn_color=(128, 0, 0), txt_color=(0xb3, 0x99, 0x22), ratio=None):
        super().__init__(geometry, frame_color, bg_color, warn_color, txt_color)

        self.orig_img = pygame.image.load(os.path.join(directory, image_file))

        self.ratio = ratio
        if self.ratio is None:
            self.ratio = calculate_ratio(self.orig_img, 0.8 * self.rect.width, 0.8 * self.rect.height)

        self.font, self.font_width = get_font("fonts/bummer.ttf", round(0.3 * self.rect.height))

    def draw(self, surface, angle, color):
        img = self.orig_img
        img = scale_image(img, self.ratio)
        img = pygame.transform.rotate(img, angle)
        surface.fill(color, self.rect)

        img_rect = img.get_rect(center=(self.rect.centerx, self.rect.y + 0.4*self.rect.height))
        surface.blit(img, img_rect)
        pygame.draw.rect(surface, self.frame_color, self.rect, 3)

        txt = self.font.render(str(abs(angle)), False, self.txt_color)
        txt_width, txt_height = txt.get_size()
        surface.blit(txt, (self.rect.centerx - 0.5 * txt_width, self.rect.bottom - txt_height - 4))


class SpeedoMeter(Meter):
    def __init__(self, geometry, frame_color=(0x98, 0x6c, 0x6a), bg_color=(0x78, 0x4f, 0x41), warn_color=(128, 0, 0),
                 txt_color=(0xb3, 0x99, 0x22), fmt="%3d"):
        super().__init__(geometry, frame_color, bg_color, warn_color, txt_color)

        self.fmt = fmt
        self.font = get_font("fonts/bummer.ttf", round(0.8 * self.rect.height))

    def draw(self, surface, speed, color):
        surface.fill(color, self.rect)
        pygame.draw.rect(surface, self.frame_color, self.rect, 3)

        blit_monospace(surface, self.rect, self.font, self.fmt % speed, self.txt_color)


class Compass(Meter):
    def __init__(self, image_file, geometry, frame_color=(0x98, 0x6c, 0x6a), bg_color=(0x78, 0x4f, 0x41),
                 warn_color=(128, 0, 0), txt_color=(0xb3, 0x99, 0x22)):
        super().__init__(geometry, frame_color, bg_color, warn_color, txt_color)

        self.orig_img = pygame.image.load(os.path.join(directory, image_file))
        self.ratio = calculate_ratio(self.orig_img, 0.8 * self.rect.width, 0.8 * self.rect.height)

    def rotate(self, angle):
        """
        Rotate a point counterclockwise by a given angle around a given origin.

        The angle should be given in radians.
        """
        angle = math.radians(angle)
        ox, oy = self.rect.center
        px, py = ox, oy - self.rect.height * 0.4

        qx = ox + math.cos(angle) * (px - ox) - math.sin(angle) * (py - oy)
        qy = oy + math.sin(angle) * (px - ox) + math.cos(angle) * (py - oy)
        return round(qx), round(qy)

    def draw(self, surface, *angles):
        surface.fill(self.bg_color, self.rect)
        pygame.draw.rect(surface, self.frame_color, self.rect, 3)

        img = self.orig_img

        img_rect = img.get_rect(center=self.rect.center)
        surface.blit(img, img_rect)
        for angle, color in angles:
            pygame.draw.circle(surface, color, self.rotate(angle), 6, 0)


def read_socket(sock, amount):
    while True:
        try:
            data = sock.recv(amount)
            if not data:
                raise RuntimeError("Socket closed")
            return data
        except socket.timeout:
            pass


def android_reader():
    global azimuth, pitch, roll, speed, bearing, gps_east, gps_north, altitude
    # Create a TCP/IP socket
    while running:
        try:
            sock = socket.socket()
            sock.settimeout(0.5)
            sock.connect(("192.168.43.1", 3451))

            print(repr(sock))

            while running:
                h = read_socket(sock, 1)
                l = read_socket(sock, 1)

                json_len = 256 * ord(h) + ord(l)

                data = bytes()
                while len(data) < json_len:
                    data += read_socket(sock, json_len - len(data))

                data = json.loads(data.decode("utf-8"))

                angles = data["orientation_angles"]
                azimuth = angles["azimuth"]
                pitch = angles["pitch"]
                roll = angles["roll"]

                loc = data["location"]
                speed = round(3.6 * loc["speed"])
                bearing = loc["bearing"]
                la = loc["latitude"]
                lo = loc["longitude"]
                gps_east, gps_north = map_maker.WGS84_to_TM35FIN(la, lo)
                altitude = loc["altitude"]

        except (RuntimeError, ConnectionError, OSError) as e:
            print(e)
            pygame.time.wait(2000)


SCREEN_RESOLUTION = (1280, 800)

directory, file = os.path.split(os.path.abspath(sys.argv[0]))

pitch = 0
roll = 0
speed = 0
azimuth = 0
bearing = 0
man_east = gps_east = 410000
man_north = gps_north = 6750000
altitude = 100
running = True


def main():
    global running

    pygame.init()

    t = threading.Thread(target=android_reader)
    t.start()

    pygame.display.set_caption("Offroad")

    try:
        main_loop()
    finally:
        pygame.display.quit()
        running = False
        t.join()


def main_loop():
    global pitch, roll, speed, gps_east, gps_north, man_east, man_north, bearing, azimuth, altitude

    screen = pygame.display.set_mode(SCREEN_RESOLUTION, pygame.FULLSCREEN)
    pygame.mouse.set_cursor((8, 8), (0, 0), (0, 0, 0, 0, 0, 0, 0, 0), (0, 0, 0, 0, 0, 0, 0, 0))
    # pygame.mouse.set_visible(False)

    clock = pygame.time.Clock()

    side = AngleMeter("images/side_profile.png", (0, 0, 300, 300))
    back = AngleMeter("images/back_profile.png", (0, 300, 300, 300), ratio=side.ratio)
    speedometer = SpeedoMeter((0, 600, 300, 100), fmt="%4s")
    altimeter = SpeedoMeter((0, 700, 300, 100), fmt="%4s")
    # magnetometer = Compass("images/compass.png", (0, 200, 200, 200))
    map = MapMaker((300, 0, 980, 800))
    map_level = 4

    mouse_sx = mouse_sy = 0
    drag = mouse_dn = False
    centered = True

    while True:
        clock.tick(20)

        for event in pygame.event.get():
            if event.type is pygame.QUIT:
                return

            if event.type is pygame.KEYDOWN and event.key == ord("+") and map_level < 10:
                map_level += 1
            if event.type is pygame.KEYDOWN and event.key == ord("-") and map_level > 2:
                map_level -= 1

            if event.type is pygame.MOUSEMOTION and mouse_dn:
                if centered:
                    man_east = gps_east
                    man_north = gps_north
                centered = False
                drag = True

                x, y = pygame.mouse.get_pos()
                de, dn = map.delta_px_to_TM35FIN(x-mouse_sx, y-mouse_sy, map_level)
                man_east -= de
                man_north += dn
                mouse_sx = x
                mouse_sy = y

            if event.type is pygame.MOUSEBUTTONDOWN:
                mouse_dn = True
                mouse_sx, mouse_sy = pygame.mouse.get_pos()
            if event.type is pygame.MOUSEBUTTONUP:
                mouse_dn = False
                if not drag:
                    x, y = pygame.mouse.get_pos()
                    if abs(x - mouse_sx) < 10 and abs(y - mouse_sy) < 10:
                        if x < 30 and y < 30:
                            return
                        elif y < SCREEN_RESOLUTION[1] / 4:
                            if map_level > 2:
                                map_level -= 1
                        elif y > 3 * SCREEN_RESOLUTION[1] / 4:
                            if map_level < 10:
                                map_level += 1
                        else:
                            centered = True

                drag = False

        key_pressed = pygame.key.get_pressed()

        if key_pressed[pygame.K_ESCAPE]:
            return

        if key_pressed[pygame.K_c]:
            centered = True

        if key_pressed[pygame.K_DOWN]:
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                pitch -= 1
            else:
                if centered:
                    man_east = gps_east
                    man_north = gps_north
                centered = False
                man_north -= map.get_step(map_level)

        if key_pressed[pygame.K_UP]:
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                pitch += 1
            else:
                if centered:
                    man_east = gps_east
                    man_north = gps_north
                centered = False
                man_north += map.get_step(map_level)

        if key_pressed[pygame.K_LEFT]:
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                roll -= 1
            else:
                if centered:
                    man_east = gps_east
                    man_north = gps_north
                centered = False
                man_east -= map.get_step(map_level)

        if key_pressed[pygame.K_RIGHT]:
            if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                roll += 1
            else:
                if centered:
                    man_east = gps_east
                    man_north = gps_north
                centered = False
                man_east += map.get_step(map_level)

        if key_pressed[pygame.K_w]:
            speed += 1
        if key_pressed[pygame.K_s]:
            speed -= 1

        if key_pressed[pygame.K_a]:
            azimuth += 1
        if key_pressed[pygame.K_d]:
            azimuth -= 1

        if key_pressed[pygame.K_q]:
            bearing += 1
        if key_pressed[pygame.K_e]:
            bearing -= 1

        screen.fill((0, 0, 0))
        side.draw(screen, pitch, side.bg_color if -50 < pitch < 50 else side.warn_color)
        back.draw(screen, -roll, back.bg_color if -35 < roll < 35 else back.warn_color)
        speedometer.draw(screen, speed, speedometer.bg_color if speed < 80 else speedometer.warn_color)
        altimeter.draw(screen, altitude, altimeter.bg_color)
        # magnetometer.draw(screen, (azimuth, (255, 0, 0)), (bearing, (0, 0, 255)))

        if centered:
            map.draw(screen, gps_east, gps_north, map_level)
        else:
            map.draw(screen, man_east, man_north, map_level)

        map.draw_fov(screen, azimuth, (255, 0, 0))
        map.draw_fov(screen, bearing, (0, 0, 255))
        # gps_bearing.draw(screen, bearing)

        pygame.display.flip()


if __name__ == "__main__":
    main()
