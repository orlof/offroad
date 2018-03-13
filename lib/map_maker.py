import urllib.request

import os
import math
from urllib.error import HTTPError

import pygame

from coordinates import WGS84lalo_to_ETRSTM35FINxy, Str_to_CoordinateValue

NORTH_BORDER = 7776640
EAST_BORDER = 733330
WEST_BORDER = 61450
SOUTH_BORDER = 6605100



START_EAST = 20000
START_NORTH = 6570000


class MapMaker(object):
    def __init__(self, geometry, frame_color=(0x98, 0x6c, 0x6a)):
        self.tiles = {}
        self.frame_color = frame_color
        self.rect = pygame.Rect(*geometry)
        self.center = 384053, 6724400

        self.crosshair = pygame.image.load("images/crosshair.png")
        self.grey_map = pygame.image.load("images/grey_map.png")
        self.crosshair_rect = (
            self.rect.centerx - self.crosshair.get_width() // 2, self.rect.centery - self.crosshair.get_height() // 2)
        self.tile_size = {2: 240000, 3: 120000, 4: 48000, 5: 24000, 6: 12000, 7: 4800, 8: 2400, 9: 1200, 10: 480}

    def valid_tile(self, tile):
        level, col, row = tile
        size = self.tile_size[level]
        e, n = self.tile_to_TM35FIN(tile)

        return e < EAST_BORDER and e + size > WEST_BORDER and n < NORTH_BORDER and n + size > SOUTH_BORDER

    def tile_to_TM35FIN(self, tile):
        level, col, row = tile
        size = self.tile_size[level]
        return START_EAST + col * size, START_NORTH + row * size

    def TM35FIN_to_tile(self, E, N, level):
        size = self.tile_size[level]
        return (E - START_EAST) // size, (N - START_NORTH) // size

    def tile_to_surface(self, tile):
        level, col, row = tile
        size = self.tile_size[level]
        west, north = size * col + START_EAST, size * (row + 1) + START_NORTH
        dE, dN = west - self.center[0], north - self.center[1]

        x = self.rect.centerx + (dE // (size // 240))
        y = self.rect.centery - (dN // (size // 240))

        return x, y

    def draw_wgs84(self, surface, la, lo, level):
        TM35FIN = WGS84lalo_to_ETRSTM35FINxy({"La": la, "Lo": lo})

        # TM35FIN = WGS84lalo_to_ETRSTM35FINxy({"La": Str_to_CoordinateValue(la), "Lo": Str_to_CoordinateValue(lo)})
        E, N = round(TM35FIN['E']), round(TM35FIN['N'])
        self.draw(surface, E, N, level)

    def draw(self, surface, E, N, level):
        self.center = E, N
        size = self.tile_size[level]
        area_width = self.rect.width * (size // 240)
        east, west = E + (area_width // 2), E - (area_width // 2)

        area_height = self.rect.height * (size // 240)
        north, south = N + (area_height // 2), N - (area_height // 2)

        start_tile = self.TM35FIN_to_tile(west, south, level)
        end_tile = self.TM35FIN_to_tile(east, north, level)

        for row in range(start_tile[1], end_tile[1] + 1):
            for col in range(start_tile[0], end_tile[0] + 1):
                self.draw_tile(surface, (level, col, row))

        pygame.draw.rect(surface, self.frame_color, self.rect, 3)
        surface.blit(self.crosshair, self.crosshair_rect)

    def draw_tile(self, surface, tile):
        if self.valid_tile(tile):
            if tile not in self.tiles:
                try:
                    if not os.path.isfile("maps/%d/%d/%d.png" % tile):
                        image_url = "http://tms.pikakartta.fi/maastokartta/%d/%d/%d.png" % tile
                        if not os.path.isdir("maps/%d/%d" % tile[:2]):
                            os.makedirs("maps/%d/%d" % tile[:2])
                        urllib.request.urlretrieve(image_url, "maps/%d/%d/%d.png" % tile)
                        print("WEB %d (%d, %d)" % tile)
                    self.tiles[tile] = pygame.image.load("maps/%d/%d/%d.png" % tile)
                except HTTPError:
                    pass

            image = self.tiles[tile]

        else:
            image = self.grey_map

        tile_x, tile_y = self.tile_to_surface(tile)
        x1 = max(self.rect.left - tile_x, 0)
        y1 = max(self.rect.top - tile_y, 0)
        w = min(tile_x + 240, self.rect.right) - max(tile_x, self.rect.left)
        h = min(tile_y + 240, self.rect.bottom) - max(tile_y, self.rect.top)
        surface.blit(image, (tile_x+x1, tile_y+y1), (x1, y1, w, h))

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

    def draw_fov(self, surface, angle, color):
        p0 = self.rect.center
        p1 = self.rotate(angle - 15)
        p2 = self.rotate(angle + 15)
        pygame.draw.polygon(surface, color, [p0, p1, p2], 2)

def main():
    pygame.init()

    # screen = pygame.display.set_mode(SCREEN_RESOLUTION, pygame.FULLSCREEN)
    pygame.display.set_caption("Carputer")

    main_loop()

    pygame.display.quit()


def main_loop():
    screen = pygame.display.set_mode(SCREEN_RESOLUTION)

    geometry = (0, 0, 800, 480)
    mm = MapMaker(geometry)

    screen.fill((255, 0, 255), geometry)

    E, N = 384053, 6724400
    level = 6

    while True:
        clock = pygame.time.Clock()
        clock.tick(10)

        for event in pygame.event.get():
            if event.type is pygame.QUIT:
                return
            if event.type is pygame.KEYDOWN and event.key == ord("+") and level < 10:
                level += 1
                print(level)
            if event.type is pygame.KEYDOWN and event.key == ord("-") and level > 2:
                level -= 1
                print(level)

        key_pressed = pygame.key.get_pressed()

        if key_pressed[pygame.K_ESCAPE]:
            return

        step = mm.tile_size[level] // 10
        if key_pressed[pygame.K_DOWN]:
            N -= step
        if key_pressed[pygame.K_UP]:
            N += step

        if key_pressed[pygame.K_LEFT]:
            E -= step
        if key_pressed[pygame.K_RIGHT]:
            E += step

        mm.draw(screen, E, N, level)
        pygame.display.flip()


SCREEN_RESOLUTION = (800, 480)

if __name__ == "__main__":
    main()

