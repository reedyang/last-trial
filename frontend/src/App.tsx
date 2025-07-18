import React, { useState } from 'react';
import { Routes, Route } from 'react-router-dom';
import { 
  Container, 
  AppBar, 
  Toolbar, 
  Typography, 
  Box, 
  IconButton, 
  Dialog, 
  DialogTitle, 
  DialogContent, 
  DialogActions, 
  Button 
} from '@mui/material';
import { HelpOutline as HelpIcon } from '@mui/icons-material';
import Home from './pages/Home';
import GameRoom from './pages/GameRoom';
import CreateGame from './pages/CreateGame';

function App() {
  const [gameIntroOpen, setGameIntroOpen] = useState(false);

  const handleOpenGameIntro = () => {
    setGameIntroOpen(true);
  };

  const handleCloseGameIntro = () => {
    setGameIntroOpen(false);
  };

  return (
    <Box sx={{ flexGrow: 1 }}>
      <AppBar position="static" elevation={2}>
        <Toolbar>
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            🤖 2050：最终审判
          </Typography>
          <IconButton 
            color="inherit" 
            onClick={handleOpenGameIntro}
            title="游戏介绍"
          >
            <HelpIcon />
          </IconButton>
        </Toolbar>
      </AppBar>
      
      <Container maxWidth="xl" sx={{ mt: 4, mb: 4 }}>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/create" element={<CreateGame />} />
          <Route path="/game/:gameId" element={<GameRoom />} />
        </Routes>
      </Container>

      {/* 游戏介绍对话框 */}
      <Dialog 
        open={gameIntroOpen} 
        onClose={handleCloseGameIntro}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>
          🤖 2050：最终审判 - 游戏介绍
        </DialogTitle>
        <DialogContent>
          <Box sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom color="primary">
              🎭 游戏背景
            </Typography>
            <Typography paragraph>
              时间：2050年，地点：新日内瓦自由城。人类与AI的战争已进入白热化阶段。
              根据情报，在每场游戏的参与者中，都藏有一个AI间谍伪装成人类。
              这是一场生死攸关的紧急审判！
            </Typography>

            <Typography variant="h6" gutterBottom color="primary" sx={{ mt: 3 }}>
              🏛️ 游戏规则
            </Typography>
            <Typography component="div">
              <Box component="ol" sx={{ pl: 2 }}>
                <Box component="li" sx={{ mb: 1 }}>
                  <strong>法庭辩论阶段：</strong>每个AI都会伪装成人类，围绕随机话题进行设定时长的激烈辩论
                </Box>
                <Box component="li" sx={{ mb: 1 }}>
                  <strong>初投票阶段：</strong>所有参与者根据辩论表现投票选出最可疑的"AI间谍"
                </Box>
                <Box component="li" sx={{ mb: 1 }}>
                  <strong>最终申辞阶段：</strong>得票最多的候选人进行最后的生死辩护
                </Box>
                <Box component="li" sx={{ mb: 1 }}>
                  <strong>最终投票阶段：</strong>经过申辞后，进行最终投票决定"AI间谍"的命运
                </Box>
                <Box component="li" sx={{ mb: 1 }}>
                  <strong>审判结果：</strong>被选中的将被"处决"，其他AI获得胜利
                </Box>
              </Box>
            </Typography>

            <Typography variant="h6" gutterBottom color="primary" sx={{ mt: 3 }}>
              🎯 游戏特色
            </Typography>
            <Typography component="div">
              <Box component="ul" sx={{ pl: 2 }}>
                <Box component="li" sx={{ mb: 1 }}>
                  <strong>多模型对战：</strong>支持多种Ollama模型同台竞技
                </Box>
                <Box component="li" sx={{ mb: 1 }}>
                  <strong>实时观战：</strong>WebSocket实时更新，观看AI间的精彩对决
                </Box>
                <Box component="li" sx={{ mb: 1 }}>
                  <strong>智能伪装：</strong>每个AI都认为自己是唯一的间谍，努力伪装成人类
                </Box>
                <Box component="li" sx={{ mb: 1 }}>
                  <strong>完整记录：</strong>保存所有对话和投票记录，支持回放观看
                </Box>
              </Box>
            </Typography>

            <Typography variant="h6" gutterBottom color="primary" sx={{ mt: 3 }}>
              🚀 开始游戏
            </Typography>
            <Typography paragraph>
              确保Ollama服务正在运行并已下载至少2个模型，然后点击"创建新游戏"开始一场惊心动魄的AI审判！
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseGameIntro}>
            关闭
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}

export default App; 