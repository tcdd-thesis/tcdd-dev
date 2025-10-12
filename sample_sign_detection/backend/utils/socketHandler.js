const { Server } = require('socket.io');

let io;
function attachSocket(server) {
  try {
    io = new Server(server, {
      cors: { origin: '*' }
    });

    io.on('connection', (socket) => {
      console.log('client connected to socket:', socket.id);
      socket.on('disconnect', () => console.log('socket disconnected:', socket.id));
    });
  } catch (e) {
    console.warn('socket.io attach failed:', e.message);
  }
}

function broadcastDetection(detection) {
  if (!io) return;
  io.emit('detection', detection);
}

module.exports = { attachSocket, broadcastDetection };
