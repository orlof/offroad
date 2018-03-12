import urllib.request

import os
import pygame

from coordinates import WGS84lalo_to_ETRSTM35FINxy, Str_to_CoordinateValue


class MapMaker(object):
    def __init__(self, geometry, frame_color=(0x98, 0x6c, 0x6a)):
        self.tiles = {}
        self.frame_color = frame_color
        self.rect = pygame.Rect(*geometry)
        self.center = 384053, 6724400

        self.crosshair = pygame.image.load("images/crosshair.png")
        self.crosshair_rect = (
            self.rect.centerx - self.crosshair.get_width() // 2, self.rect.centery - self.crosshair.get_height() // 2)

    @staticmethod
    def TM35FIN_to_tile(E, N):
        return (E - 20000) // 480, (N - 6570000) // 480

    def tile_to_surface(self, tile):
        col, row = tile
        west, north = 480 * col + 20000, 480 * (row + 1) + 6570000
        dE, dN = west - self.center[0], north - self.center[1]

        x = self.rect.centerx + (dE // 2)
        y = self.rect.centery - (dN // 2)

        return x, y

    def draw_wgs84(self, surface, la, lo):
        TM35FIN = WGS84lalo_to_ETRSTM35FINxy({"La": la, "Lo": lo})

        # TM35FIN = WGS84lalo_to_ETRSTM35FINxy({"La": Str_to_CoordinateValue(la), "Lo": Str_to_CoordinateValue(lo)})
        E, N = round(TM35FIN['E']), round(TM35FIN['N'])
        self.draw(surface, E, N)

        # self.draw(surface, 384053, 6724400)

    def draw(self, surface, E, N):
        if 70000 < E < 733000 and 6600000 < N < 7770000:
            self.center = E, N
            east, west = E + self.rect.width, E - self.rect.width
            north, south = N + self.rect.height, N - self.rect.height

            start_tile = self.TM35FIN_to_tile(west, south)
            end_tile = self.TM35FIN_to_tile(east, north)

            for row in range(start_tile[1], end_tile[1] + 1):
                for col in range(start_tile[0], end_tile[0] + 1):
                    self.draw_tile(surface, (col, row))

        pygame.draw.rect(surface, self.frame_color, self.rect, 3)
        surface.blit(self.crosshair, self.crosshair_rect)

    def draw_tile(self, surface, tile):
        if tile not in self.tiles:
            if not os.path.isfile("maps/%d/%d.png" % tile):
                image_url = "http://tms.pikakartta.fi/maastokartta/10/%d/%d.png" % tile
                if not os.path.isdir("maps/%d" % tile[0]):
                    os.makedirs("maps/%d" % tile[0])
                urllib.request.urlretrieve(image_url, "maps/%d/%d.png" % tile)
            self.tiles[tile] = pygame.image.load("maps/%d/%d.png" % tile)

        image = self.tiles[tile]
        tile_x, tile_y = self.tile_to_surface(tile)
        x1 = max(self.rect.left - tile_x, 0)
        y1 = max(self.rect.top - tile_y, 0)
        w = min(tile_x + 240, self.rect.right) - max(tile_x, self.rect.left)
        h = min(tile_y + 240, self.rect.bottom) - max(tile_y, self.rect.top)
        surface.blit(image, (tile_x+x1, tile_y+y1), (x1, y1, w, h))


def main():
    pygame.init()

    # screen = pygame.display.set_mode(SCREEN_RESOLUTION, pygame.FULLSCREEN)
    pygame.display.set_caption("Carputer")

    main_loop()

    pygame.display.quit()


def main_loop():
    screen = pygame.display.set_mode(SCREEN_RESOLUTION)

    geometry = (100, 100, 500, 300)
    mm = MapMaker(geometry)

    screen.fill((255, 0, 255), geometry)

    E, N = 384053, 6724400

    while True:
        clock = pygame.time.Clock()
        # clock.tick(100)

        for event in pygame.event.get():
            if event.type is pygame.QUIT:
                return

        key_pressed = pygame.key.get_pressed()

        if key_pressed[pygame.K_ESCAPE]:
            return

        if key_pressed[pygame.K_DOWN]:
            N -= 10
        if key_pressed[pygame.K_UP]:
            N += 10

        if key_pressed[pygame.K_LEFT]:
            E -= 10
        if key_pressed[pygame.K_RIGHT]:
            E += 10

        mm.draw(screen, E, N)
        pygame.display.flip()


SCREEN_RESOLUTION = (800, 480)

if __name__ == "__main__":
    main()

