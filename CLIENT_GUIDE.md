# CourtChime - Pickleball Session Management

## What is CourtChime?

CourtChime is a mobile application designed to manage pickleball sessions, including player registration, match scheduling, scoring, and performance tracking. It handles everything from match generation to player rotations and real-time score updates.

## Why Use CourtChime?

- **Automated Match Scheduling**: Generates fair matches based on player categories, ratings, and previous partnerships
- **Flexible Court Management**: Maximizes court usage and minimizes player sitouts
- **Multiple Rotation Models**: Choose between Legacy (round-robin) or Top Court (competitive ladder)
- **Real-Time Tracking**: Live score updates, timer management, and session controls
- **Performance Analytics**: Track wins, losses, ratings, and recent form for all players

## Legacy Court Mode

**How It Works:**
- Players are shuffled and redistributed each round
- Matches are generated using round-robin logic with partner/opponent history
- Players who haven't partnered together recently are paired
- Focus on variety and ensuring everyone plays with different people
- Rating changes occur after each match based on performance

**Best For:** Recreational play, social sessions, rotating partners

## Top Court Mode

**How It Works:**
- Court 1 is designated as the "Top Court" (most competitive)
- **Winners move up:** Players who win on lower courts advance one court up
- **Losers stay (except Court 1):** Players who lose remain on the same court
- **Court 1 special rule:** Winners stay on Court 1, losers move to the bottom court
- **Team splitting:** After each match, partners split and play AGAINST each other in the next round
- Players are ranked by total wins (not ratings)
- No rating changes - cumulative wins determine standings

**Best For:** Competitive sessions, tournament-style play, skill-based progression

## Rating System

CourtChime uses **DUPR-style ELO rating logic**:
- All players start at 3.00
- Ratings adjust based on match outcomes and opponent ratings
- Winning against higher-rated opponents increases your rating more
- Losing to lower-rated opponents decreases your rating more
- Ratings range typically from 2.00 (beginner) to 5.50+ (advanced)
- Only applies to Legacy mode (Top Court uses win counts instead)

## Additional Features

- **Social Category**: Optional non-competitive play with no rating impacts
- **Manual Sitout Management**: Drag and drop players between courts and sitout area
- **Cross-Category Play**: Option to mix players from different skill levels
- **Maximize Courts**: Automatically fills all available courts before any player sits out
- **Recent Form Tracking**: View last 5 results (W=Win, L=Loss, S=Sitout) for each player

---

**Note:** The app is designed for both casual recreational play (Legacy) and competitive tournament-style sessions (Top Court). Choose the mode that best fits your group's preferences.
