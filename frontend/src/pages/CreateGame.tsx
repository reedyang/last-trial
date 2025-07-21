import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  TextField,
  Paper,
  Grid,
  Card,
  CardContent,
  CircularProgress,
  Alert,
  Chip,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  FormControlLabel,
  Checkbox,
  FormGroup
} from '@mui/material';
import { ArrowBack as BackIcon, PlayArrow as StartIcon } from '@mui/icons-material';
import { gameService } from '../services/gameService';
import { ollamaService, ModelInfo } from '../services/ollamaService';

const CreateGame: React.FC = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [models, setModels] = useState<ModelInfo[]>([]);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [loadingModels, setLoadingModels] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [dialogContent, setDialogContent] = useState({ title: '', message: '', isSuccess: false });
  const [formData, setFormData] = useState({
    max_round_time: 600
  });
  const [createdGameId, setCreatedGameId] = useState<number | null>(null);

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      const modelsData = await ollamaService.getModels();
      setModels(modelsData);
      // 默认选择所有模型
      setSelectedModels(modelsData.map(model => model.name));
    } catch (error) {
      console.error('获取模型列表失败:', error);
    } finally {
      setLoadingModels(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    try {
      const gameData = {
        ...formData,
        selected_models: selectedModels.length > 0 ? selectedModels : undefined
      };
      const game = await gameService.createGame(gameData);
      setCreatedGameId(game.id);
      setDialogContent({
        title: '🎉 审判启动成功',
        message: `紧急法庭已就绪！\n游戏ID: ${game.id}\n\n所有AI参与者已准备完毕，等待您的指令开始这场生死审判...`,
        isSuccess: true
      });
      setDialogOpen(true);
    } catch (error) {
      setDialogContent({
        title: '❌ 审判启动失败',
        message: `法庭系统出现故障：\n${(error as Error).message}\n\n请检查系统状态后重试。`,
        isSuccess: false
      });
      setDialogOpen(true);
    } finally {
      setLoading(false);
    }
  };

  const handleDialogClose = () => {
    setDialogOpen(false);
    if (dialogContent.isSuccess && createdGameId) {
      navigate(`/game/${createdGameId}`);
    }
  };

  const handleInputChange = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.type === 'checkbox' ? e.target.checked : parseInt(e.target.value);
    setFormData(prev => ({
      ...prev,
      [field]: value
    }));
  };

  const handleModelToggle = (modelName: string) => {
    setSelectedModels(prev => {
      if (prev.includes(modelName)) {
        return prev.filter(name => name !== modelName);
      } else {
        return [...prev, modelName];
      }
    });
  };

  const isExternalModel = (modelName: string) => {
    return modelName.startsWith('external:');
  };

  const getModelDisplayName = (modelName: string) => {
    return isExternalModel(modelName) ? modelName.replace('external:', '') : modelName;
  };

  return (
    <Box>
      <Box display="flex" alignItems="center" mb={3}>
        <Button
          startIcon={<BackIcon />}
          onClick={() => navigate('/')}
          sx={{ mr: 2 }}
        >
          返回首页
        </Button>
        <Typography variant="h4" component="h1">
          创建新游戏
        </Typography>
      </Box>

      <Grid container spacing={3}>
        {/* 模型选择 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
              <Typography variant="h6">
                选择AI模型 ({selectedModels.length}/{models.length})
              </Typography>
              <Box>
                <Button 
                  size="small" 
                  onClick={() => setSelectedModels(models.map(m => m.name))}
                  disabled={selectedModels.length === models.length}
                >
                  全选
                </Button>
                <Button 
                  size="small" 
                  onClick={() => setSelectedModels([])}
                  disabled={selectedModels.length === 0}
                  sx={{ ml: 1 }}
                >
                  全不选
                </Button>
              </Box>
            </Box>

            {loadingModels ? (
              <Box display="flex" justifyContent="center" p={2}>
                <CircularProgress />
              </Box>
            ) : models.length === 0 ? (
              <Alert severity="error">
                未检测到可用模型。请确保Ollama正在运行并已下载模型，或添加外部模型。
              </Alert>
            ) : (
              <>
                                 <Alert 
                   severity={selectedModels.length >= 3 ? "success" : "warning"} 
                   sx={{ mb: 2 }}
                 >
                   {selectedModels.length >= 3 
                     ? `已选择 ${selectedModels.length} 个模型，满足审判要求！` 
                     : `至少需要选择 3 个模型参与审判`
                   }
                 </Alert>
                
                <FormGroup sx={{ maxHeight: 200, overflow: 'auto' }}>
                  {models.map((model) => (
                    <FormControlLabel
                      key={model.name}
                      control={
                        <Checkbox
                          checked={selectedModels.includes(model.name)}
                          onChange={() => handleModelToggle(model.name)}
                          size="small"
                        />
                      }
                      label={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="body2">
                            {getModelDisplayName(model.name)}
                          </Typography>
                          {isExternalModel(model.name) && (
                            <Chip 
                              label="外部" 
                              size="small" 
                              color="secondary" 
                              variant="outlined"
                            />
                          )}
                        </Box>
                      }
                      sx={{ '& .MuiFormControlLabel-label': { width: '100%' } }}
                    />
                  ))}
                </FormGroup>

                <Typography variant="body2" sx={{ mt: 2, color: 'text.secondary' }}>
                  审判将从选中的模型中分配AI参与者，进行终极身份伪装对抗。
                </Typography>
              </>
            )}

                         {selectedModels.length < 3 && (
               <Alert severity="warning" sx={{ mt: 2 }}>
                 当前选择模型数量 ({selectedModels.length}) 少于最少要求 (3个)。
                 请选择更多模型参与审判。
               </Alert>
             )}
          </Paper>
        </Grid>

        {/* 游戏设置 */}
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              游戏设置
            </Typography>
            
            <Box component="form" onSubmit={handleSubmit}>
              <TextField
                fullWidth
                label="审判时长（秒）"
                type="number"
                value={formData.max_round_time}
                onChange={handleInputChange('max_round_time')}
                margin="normal"
                inputProps={{ min: 60, max: 1800 }}
                helperText="建议 600 秒（10分钟）进行完整辩论"
              />
              
              <Alert severity="info" sx={{ mt: 2 }}>
                参与者数量将根据您选择的AI模型数量自动确定
              </Alert>

              <Divider sx={{ my: 2 }} />

              <Button
                type="submit"
                variant="contained"
                size="large"
                startIcon={<StartIcon />}
                disabled={loading || selectedModels.length < 3}
                fullWidth
                sx={{ mt: 2 }}
              >
                {loading ? <CircularProgress size={24} /> : '创建游戏'}
              </Button>
            </Box>
          </Paper>
        </Grid>
      </Grid>

      {/* 游戏说明 */}
      <Paper sx={{ p: 3, mt: 3 }}>
        <Typography variant="h6" gutterBottom>
          《2050：最终审判》游戏规则
        </Typography>
        <Grid container spacing={2}>
          <Grid item xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" color="primary" gutterBottom>
                  1. 背景设定
                </Typography>
                <Typography variant="body2">
                  2050年，AI与人类战争后的紧急法庭。观众认为有1个AI间谍，但所有参与者都是AI
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" color="primary" gutterBottom>
                  2. 身份设定
                </Typography>
                <Typography variant="body2">
                  所有参与者都是AI，但互相不知道。每个AI都认为自己是唯一的间谍
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" color="primary" gutterBottom>
                  3. 法庭辩论
                </Typography>
                <Typography variant="body2">
                  设定时长的激烈辩论，每个AI都要伪装成人类，证明自己的人类身份
                </Typography>
              </CardContent>
            </Card>
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle2" color="primary" gutterBottom>
                  4. 最终审判
                </Typography>
                <Typography variant="body2">
                  投票选出最可疑者。没有被选中的AI获胜，被选中的AI失败
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        </Grid>
      </Paper>

      <Dialog open={dialogOpen} onClose={handleDialogClose} maxWidth="sm" fullWidth>
        <DialogTitle sx={{ 
          color: dialogContent.isSuccess ? 'success.main' : 'error.main',
          fontWeight: 'bold'
        }}>
          {dialogContent.title}
        </DialogTitle>
        <DialogContent>
          <Typography 
            variant="body1" 
            sx={{ 
              whiteSpace: 'pre-line',
              color: 'text.primary'
            }}
          >
            {dialogContent.message}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={handleDialogClose} 
            color={dialogContent.isSuccess ? 'success' : 'primary'}
            variant="contained"
          >
            {dialogContent.isSuccess ? '进入审判室' : '关闭'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default CreateGame; 