### Controls

`← → ↑ ↓` Move your ship
`SPACE` Fire your cannon
`ESC` Quit to menu

### Screens

| Screen | Description |
| --- | --- |
| Name Entry | Enter your pilot callsign (2–16 chars) |
| Main Menu | Basic controls and game objective |
| Gameplay | 3 waves with on-screen HUD and instructions |
| Result | Win or Game Over outcome with final score |
| Leaderboard | Top 5 all-time scores from SQLite3 |

## Project Structure

### Project Structure

```text
project/
├── main.py             
├── requirements.txt     
├── .gitignore
├── README.md
├── src/
│   └── space_shooter.py 
└── assets/
    ├── enemy.png            
    └── player.png
```



## Architecture & OOP

The project is structured around five classes:

```text
DatabaseLogger   <-- SQLite3 persistence (save scores, fetch top-5)

     |
     +-- used by --> Game 
                    |
                    +-- Player   (controls, lives, score)
                    +-- Enemy    (wave-scale stats, group movement)
                    +-- Bullet  
``` 

| Class | Responsibility |
| --- | --- |
| `DatabaseLogger` | Creates `scores.db`, saves each result, returns top-5 |
| `Player` | Movement, shooting cooldown, life and score tracking |
| `Enemy` | HP, speed, and fire-rate scaled by wave; group movement mechanics |
| `Bullet` | Travels up (player) or down (enemy); auto-destroys off-screen |
| `Game` | Screen lifecycle, HUD rendering, collision detection, main loop |

## Leaderboard

Scores are saved to a local SQLite3 database (`scores.db`) at the end of every session, regardless of a win or loss. The leaderboard screen shows the all-time top 5 pilots sorted by score.

The `DatabaseLogger` class handles all DB interaction:

db = DatabaseLogger()        # creates table if not exists
db.save("Alice", 480, True)  # save a result
db.top5()                    # returns [(name, score, won), ...]

## Tech Stack

* Python 3.9+
* Pygame 2.5
* SQLite3
