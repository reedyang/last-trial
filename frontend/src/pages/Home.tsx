import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Card,
  CardContent,
  Typography,
  Button,
  Grid,
  Chip,
  Alert,
  CircularProgress,
  Paper,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogContentText,
  DialogActions
} from '@mui/material';
import {
  Add as AddIcon,
  PlayArrow as PlayIcon,
  Refresh as RefreshIcon,
  Delete as DeleteIcon
} from '@mui/icons-material';
import { gameService } from '../services/gameService';
import { ollamaService } from '../services/ollamaService';

interface Game {
  id: number;
  status: string;
  start_time: string;
  total_rounds: number;
  winner_count: number;
}

interface ModelInfo {
  name: string;
  size?: string;
  family?: string;
}

const Home: React.FC = () => {
  const navigate = useNavigate();
  const [games, setGames] = useState<Game[]>([]);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [ollamaStatus, setOllamaStatus] = useState<'checking' | 'healthy' | 'error'>('checking');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [gameToDelete, setGameToDelete] = useState<number | null>(null);
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      // 检查Ollama状态
      const healthCheck = await ollamaService.checkHealth();
      setOllamaStatus(healthCheck.ollama_available ? 'healthy' : 'error');

      // 获取游戏列表
      const gamesData = await gameService.getGames();
      setGames(gamesData);

      // 获取模型列表
      if (healthCheck.ollama_available) {
        const modelsData = await ollamaService.getModels();
        setModels(modelsData);
      }
    } catch (error) {
      console.error('加载数据失败:', error);
      setOllamaStatus('error');
    } finally {
      setLoading(false);
    }
  };

  const handleDeleteGame = async (gameId: number) => {
    setGameToDelete(gameId);
    setDeleteDialogOpen(true);
  };

  const confirmDelete = async () => {
    if (!gameToDelete) return;
    
    setDeleting(true);
    try {
      await gameService.deleteGame(gameToDelete);
      setGames(games.filter(game => game.id !== gameToDelete));
      setDeleteDialogOpen(false);
      setGameToDelete(null);
    } catch (error) {
      console.error('删除游戏失败:', error);
      alert('删除游戏失败: ' + (error as Error).message);
    } finally {
      setDeleting(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running': return 'success';
      case 'finished': return 'default';
      case 'preparing': return 'warning';
      default: return 'default';
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'running': return '审判中';
      case 'finished': return '审判结束';
      case 'preparing': return '准备中';
      default: return status;
    }
  };

  const formatDateTime = (timestamp: string | Date) => {
    let date: Date;
    
    if (typeof timestamp === 'string') {
      // 解析时间戳字符串
      date = new Date(timestamp);
      
      // 检查是否解析成功
      if (isNaN(date.getTime())) {
        console.error('无效的时间戳格式:', timestamp);
        return '无效时间';
      }
    } else {
      date = timestamp;
    }
    
    // 使用Intl.DateTimeFormat确保使用本地时区
    try {
      const formatter = new Intl.DateTimeFormat(navigator.language, {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
        hour12: false,
        timeZone: Intl.DateTimeFormat().resolvedOptions().timeZone
      });
      
      return formatter.format(date);
    } catch (error) {
      console.error('时间格式化错误:', error);
      // 降级到基本的toLocaleString
      return date.toLocaleString();
    }
  };

  return (
    <Box>
      {/* 状态卡片 */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                Ollama状态
              </Typography>
              {ollamaStatus === 'checking' && (
                <Box display="flex" alignItems="center">
                  <CircularProgress size={20} sx={{ mr: 1 }} />
                  <Typography>检查中...</Typography>
                </Box>
              )}
              {ollamaStatus === 'healthy' && (
                <Alert severity="success" sx={{ mt: 1 }}>
                  Ollama服务正常 ({models.length} 个模型可用)
                </Alert>
              )}
              {ollamaStatus === 'error' && (
                <Alert severity="error" sx={{ mt: 1 }}>
                  Ollama服务不可用
                </Alert>
              )}
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                可用模型
              </Typography>
              <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
                {models.slice(0, 3).map((model) => (
                  <Chip 
                    key={model.name} 
                    label={model.name} 
                    variant="outlined" 
                    size="small"
                  />
                ))}
                {models.length > 3 && (
                  <Chip 
                    label={`+${models.length - 3} 更多`} 
                    variant="outlined" 
                    size="small"
                    color="primary"
                  />
                )}
              </Box>
            </CardContent>
          </Card>
        </Grid>
        
        <Grid item xs={12} md={4}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>
                快速开始
              </Typography>
              <Button
                variant="contained"
                startIcon={<AddIcon />}
                fullWidth
                onClick={() => navigate('/create')}
                disabled={ollamaStatus !== 'healthy' || models.length < 2}
                sx={{ mt: 1 }}
              >
                创建新游戏
              </Button>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* 游戏列表 */}
      <Paper sx={{ p: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h5">
            游戏列表
          </Typography>
          <IconButton onClick={loadData} disabled={loading}>
            <RefreshIcon />
          </IconButton>
        </Box>

        {loading ? (
          <Box display="flex" justifyContent="center" p={4}>
            <CircularProgress />
          </Box>
        ) : games.length === 0 ? (
          <Alert severity="info">
            暂无游戏，点击"创建新游戏"开始！
          </Alert>
        ) : (
          <List>
            {games.map((game) => (
              <ListItem key={game.id} divider>
                <ListItemText
                  primary={
                    <Box display="flex" alignItems="center" gap={1}>
                      <Typography variant="h6">
                        游戏 #{game.id}
                      </Typography>
                      <Chip
                        label={getStatusText(game.status)}
                        color={getStatusColor(game.status) as any}
                        size="small"
                      />
                    </Box>
                  }
                  secondary={
                    <Box>
                      <Typography variant="body2" color="text.secondary">
                        开始时间: {formatDateTime(game.start_time)}
                      </Typography>
                    </Box>
                  }
                />
                <ListItemSecondaryAction>
                  <Box display="flex" gap={1}>
                    <Button
                      variant="outlined"
                      size="small"
                      startIcon={<PlayIcon />}
                      onClick={() => navigate(`/game/${game.id}`)}
                    >
                      {game.status === 'finished' ? '观看回放' : '观看'}
                    </Button>
                    <IconButton
                      size="small"
                      color="error"
                      onClick={() => handleDeleteGame(game.id)}
                      title="删除游戏"
                    >
                      <DeleteIcon />
                    </IconButton>
                  </Box>
                </ListItemSecondaryAction>
              </ListItem>
            ))}
          </List>
        )}
      </Paper>

      {/* 删除确认对话框 */}
      <Dialog open={deleteDialogOpen} onClose={() => setDeleteDialogOpen(false)}>
        <DialogTitle>确认删除</DialogTitle>
        <DialogContent>
          <DialogContentText>
            您确定要删除游戏 #{gameToDelete} 吗？此操作无法撤销，将删除游戏的所有数据包括聊天记录。
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={deleting}>
            取消
          </Button>
          <Button onClick={confirmDelete} color="error" disabled={deleting}>
            {deleting ? '删除中...' : '确认删除'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default Home; 