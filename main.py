import pygame
import pygame_menu
import sys
import pygame_gui
import random
pygame.init()

# scr - screen
scr = pygame.display.set_mode((900, 900), pygame.RESIZABLE)
manager = pygame_gui.UIManager((800, 600), "resources/theme.json")
pygame.display.set_caption("D&D Companion")
icon = pygame.image.load('images/dice.png')
pygame.display.set_icon(icon)
fps_clock = pygame.time.Clock()

# drag n drop
map = pygame.image.load('images/dice.png')
maprec = map.get_rect()
maprec.center = (200, 300)
boxes = []
for i in range(5):
  x = random.randint(50, 700)
  y = random.randint(50, 350)
  w = random.randint(35, 65)
  h = random.randint(35, 65)
  box = pygame.Rect(x, y, w, h)
  boxes.append(box)
active_box = None
# ui for battle
char_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((350, 400), (100, 50)),
                                            text='CHARACTER',
                                            manager=manager)
actions_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((350, 275), (100, 50)),
                                            text='ACTIONS',
                                            manager=manager)






# main loop
running = True
while running:
    time_delta = fps_clock.tick(60) / 1000.0
    scr.fill((100, 50, 50))
    scr.blit(map,maprec) # draw map surface on scr
    for box in boxes:
        pygame.draw.rect(scr, "white", box)
    for event in pygame.event.get():
        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                for num, box in enumerate(boxes):
                    if box.collidepoint(event.pos):
                        active_box = num
        if event.type == pygame.MOUSEBUTTONUP:
            if event.button == 1:
                active_box = None
        if event.type == pygame.MOUSEMOTION:
            if active_box is not None:
                boxes[active_box].move_ip(event.rel)
        if event.type == pygame.QUIT:
            running = False
            pygame.quit()
            sys.exit()
        if event.type == pygame_gui.UI_BUTTON_PRESSED:
            if event.ui_element == char_button:
                print('Hello World!')
        manager.process_events(event)
    manager.update(time_delta)
    manager.draw_ui(scr)

    pygame.display.update()
    fps_clock.tick(60)
