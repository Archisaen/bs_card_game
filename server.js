const express = require('express');
const path = require('path');
const { createServer } = require('http');
const { Server } = require('socket.io');

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer);

const PORT = process.env.PORT || 3000;

// Game rooms storage
const gameRooms = new Map();

// Serve static files
app.use(express.static(__dirname));

// Serve the multiplayer game
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'card_game_multiplayer.html'));
});

// Serve the single-player version
app.get('/singleplayer', (req, res) => {
    res.sendFile(path.join(__dirname, 'card_game.html'));
});

// Generate random room code
function generateRoomCode() {
    return Math.random().toString(36).substring(2, 8).toUpperCase();
}

// Socket.io connection handling
io.on('connection', (socket) => {
    console.log('User connected:', socket.id);

    // Create new game room
    socket.on('createRoom', (playerName) => {
        const roomCode = generateRoomCode();
        const room = {
            code: roomCode,
            players: [{ id: socket.id, name: playerName, ready: false }],
            gameState: null,
            started: false
        };
        gameRooms.set(roomCode, room);
        socket.join(roomCode);
        socket.emit('roomCreated', { roomCode, playerId: socket.id });
        console.log(`Room ${roomCode} created by ${playerName}`);
    });

    // Join existing room
    socket.on('joinRoom', ({ roomCode, playerName }) => {
        const room = gameRooms.get(roomCode);
        if (!room) {
            socket.emit('error', 'Room not found');
            return;
        }
        if (room.started) {
            socket.emit('error', 'Game already started');
            return;
        }
        if (room.players.length >= 5) {
            socket.emit('error', 'Room is full');
            return;
        }

        room.players.push({ id: socket.id, name: playerName, ready: false });
        socket.join(roomCode);
        socket.emit('roomJoined', { roomCode, playerId: socket.id });

        // Notify all players in room
        io.to(roomCode).emit('playersUpdate', room.players);
        console.log(`${playerName} joined room ${roomCode}`);
    });

    // Player ready
    socket.on('playerReady', (roomCode) => {
        const room = gameRooms.get(roomCode);
        if (!room) return;

        const player = room.players.find(p => p.id === socket.id);
        if (player) {
            player.ready = true;
            io.to(roomCode).emit('playersUpdate', room.players);

            // Check if all players ready and at least 2 players
            if (room.players.length >= 2 && room.players.every(p => p.ready)) {
                room.started = true;
                io.to(roomCode).emit('gameStart', room.players);
            }
        }
    });

    // Game state update
    socket.on('gameStateUpdate', ({ roomCode, gameState }) => {
        const room = gameRooms.get(roomCode);
        if (!room) return;

        room.gameState = gameState;
        // Broadcast to all OTHER players in room
        socket.to(roomCode).emit('gameStateChanged', gameState);
    });

    // Player action (play cards, pick up pile, etc)
    socket.on('playerAction', ({ roomCode, action, data }) => {
        io.to(roomCode).emit('playerAction', { playerId: socket.id, action, data });
    });

    // Disconnect
    socket.on('disconnect', () => {
        console.log('User disconnected:', socket.id);

        // Remove player from all rooms
        gameRooms.forEach((room, roomCode) => {
            const playerIndex = room.players.findIndex(p => p.id === socket.id);
            if (playerIndex !== -1) {
                room.players.splice(playerIndex, 1);

                if (room.players.length === 0) {
                    gameRooms.delete(roomCode);
                    console.log(`Room ${roomCode} deleted (empty)`);
                } else {
                    io.to(roomCode).emit('playersUpdate', room.players);
                    io.to(roomCode).emit('playerDisconnected', socket.id);
                }
            }
        });
    });
});

httpServer.listen(PORT, () => {
    console.log(`Card game server running on port ${PORT}`);
});
