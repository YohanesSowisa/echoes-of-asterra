"""
Echoes of Asterra - Collision System
Handles axis-aligned bounding box (AABB) checks, movement resolution, and spatial grid lookups.
"""
import pygame
from typing import List, Any

class CollisionSystem:
    """
    Coordinates solid tile collisions, entity-to-entity overlaps,
    and attack range queries using spatial bounding boxes.
    """
    @staticmethod
    def check_tile_collision(rect: pygame.Rect, solid_tiles: List[pygame.Rect]) -> bool:
        """Returns True if the rect collides with any solid tile rect."""
        return rect.collidelist(solid_tiles) != -1

    @staticmethod
    def resolve_movement(entity: Any, solid_tiles: List[pygame.Rect], direction: str) -> None:
        """
        Resolves entity movement along the X or Y axes, snapping back
        on collision with solid tiles. Modifies entity.hitbox and entity.pos.
        """
        # Determine movement axis
        if direction == 'x':
            # Check collisions with neighboring solid rects
            for tile_rect in solid_tiles:
                if entity.hitbox.colliderect(tile_rect):
                    # Colliding on X axis
                    if entity.velocity.x > 0:
                        # Moving right: snap to tile's left
                        entity.hitbox.right = tile_rect.left
                    elif entity.velocity.x < 0:
                        # Moving left: snap to tile's right
                        entity.hitbox.left = tile_rect.right
                    # Update actual vector position
                    entity.pos.x = entity.hitbox.centerx
                    entity.rect.centerx = entity.hitbox.centerx
        
        elif direction == 'y':
            for tile_rect in solid_tiles:
                if entity.hitbox.colliderect(tile_rect):
                    # Colliding on Y axis
                    if entity.velocity.y > 0:
                        # Moving down: snap to tile's top
                        entity.hitbox.bottom = tile_rect.top
                    elif entity.velocity.y < 0:
                        # Moving up: snap to tile's bottom
                        entity.hitbox.top = tile_rect.bottom
                    # Update actual vector position
                    entity.pos.y = entity.hitbox.centery
                    entity.rect.centery = entity.hitbox.centery

    @staticmethod
    def get_nearby_solids(entity_hitbox: pygame.Rect, tile_grid: List[List[str]], tile_size: int) -> List[pygame.Rect]:
        """
        Returns a list of solid tile Rects adjacent to the entity's hitbox,
        optimizing collision checks by ignoring distant tiles.
        """
        solids = []
        
        # Determine grid indices occupied by the hitbox
        start_col = max(0, entity_hitbox.left // tile_size)
        end_col = min(len(tile_grid[0]) - 1, entity_hitbox.right // tile_size)
        start_row = max(0, entity_hitbox.top // tile_size)
        end_row = min(len(tile_grid) - 1, entity_hitbox.bottom // tile_size)
        
        # Add 1 tile padding around indices
        start_col = max(0, start_col - 1)
        end_col = min(len(tile_grid[0]) - 1, end_col + 1)
        start_row = max(0, start_row - 1)
        end_row = min(len(tile_grid) - 1, end_row + 1)
        
        # Build list of solid rects
        for r in range(start_row, end_row + 1):
            for c in range(start_col, end_col + 1):
                tile_type = tile_grid[r][c]
                # 'wall', 'tree', 'burnt_tree', 'snow_tree' and 'water' are solid tiles
                if tile_type in ['wall', 'tree', 'water', 'burnt_tree', 'snow_tree']:
                    solids.append(pygame.Rect(c * tile_size, r * tile_size, tile_size, tile_size))
                    
        return solids
