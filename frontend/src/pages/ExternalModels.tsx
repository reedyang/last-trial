import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  FormControlLabel,
  Alert,
  CircularProgress,
  Tooltip,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem
} from '@mui/material';
import {
  Add as AddIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  Science as TestIcon,
  Refresh as RefreshIcon,
  ArrowBack as ArrowBackIcon
} from '@mui/icons-material';
import { 
  externalModelService, 
  ExternalModel, 
  ExternalModelCreate, 
  ExternalModelUpdate,
  ExternalModelTestResponse,
  APIType
} from '../services/externalModelService';

const ExternalModels: React.FC = () => {
  const navigate = useNavigate();
  const [models, setModels] = useState<ExternalModel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingModel, setEditingModel] = useState<ExternalModel | null>(null);
  const [testingModel, setTestingModel] = useState<number | null>(null);
  const [testResult, setTestResult] = useState<ExternalModelTestResponse | null>(null);

  // 表单状态
  const [formData, setFormData] = useState<ExternalModelCreate>({
    name: '',
    api_type: APIType.OPENAI,
    api_url: '',
    model_id: '',
    api_key: '',
    description: '',
    is_active: true
  });

  useEffect(() => {
    loadModels();
  }, []);

  const loadModels = async () => {
    try {
      setLoading(true);
      const data = await externalModelService.getModels();
      setModels(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : '加载模型列表失败');
    } finally {
      setLoading(false);
    }
  };

  const getAPITypeLabel = (apiType: APIType): string => {
    switch (apiType) {
      case APIType.OPENAI:
        return 'OpenAI API';
      case APIType.OPENWEBUI:
        return 'OpenWebUI API';
      default:
        return 'Unknown';
    }
  };

  const getAPITypeColor = (apiType: APIType): 'primary' | 'secondary' => {
    return apiType === APIType.OPENAI ? 'primary' : 'secondary';
  };

  const getPlaceholderURL = (apiType: APIType): string => {
    switch (apiType) {
      case APIType.OPENAI:
        return 'https://api.openai.com/v1/chat/completions 或 http://localhost:11434/v1/chat/completions';
      case APIType.OPENWEBUI:
        return 'http://localhost:3000/api/chat/completions';
      default:
        return '';
    }
  };

  const handleOpenDialog = (model?: ExternalModel) => {
    if (model) {
      setEditingModel(model);
      setFormData({
        name: model.name,
        api_type: model.api_type,
        api_url: model.api_url,
        model_id: model.model_id,
        api_key: model.api_key || '',
        description: model.description || '',
        is_active: model.is_active
      });
    } else {
      setEditingModel(null);
      setFormData({
        name: '',
        api_type: APIType.OPENAI,
        api_url: '',
        model_id: '',
        api_key: '',
        description: '',
        is_active: true
      });
    }
    setDialogOpen(true);
    setTestResult(null);
  };

  const handleCloseDialog = () => {
    setDialogOpen(false);
    setEditingModel(null);
    setTestResult(null);
  };

  const handleSave = async () => {
    try {
      setError(null);
      
      if (editingModel) {
        // 更新模型
        const updateData: ExternalModelUpdate = {};
        if (formData.name !== editingModel.name) updateData.name = formData.name;
        if (formData.api_type !== editingModel.api_type) updateData.api_type = formData.api_type;
        if (formData.api_url !== editingModel.api_url) updateData.api_url = formData.api_url;
        if (formData.model_id !== editingModel.model_id) updateData.model_id = formData.model_id;
        if (formData.api_key !== (editingModel.api_key || '')) updateData.api_key = formData.api_key;
        if (formData.description !== (editingModel.description || '')) updateData.description = formData.description;
        if (formData.is_active !== editingModel.is_active) updateData.is_active = formData.is_active;
        
        await externalModelService.updateModel(editingModel.id, updateData);
      } else {
        // 创建新模型
        await externalModelService.createModel(formData);
      }
      
      handleCloseDialog();
      await loadModels();
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败');
    }
  };

  const handleDelete = async (model: ExternalModel) => {
    if (!window.confirm(`确定要删除模型 "${model.name}" 吗？`)) {
      return;
    }

    try {
      setError(null);
      await externalModelService.deleteModel(model.id);
      await loadModels();
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败');
    }
  };

  const handleTest = async (model?: ExternalModel) => {
    try {
      setError(null);
      setTestResult(null);
      
      let result: ExternalModelTestResponse;
      
      if (model) {
        // 测试已存在的模型
        setTestingModel(model.id);
        result = await externalModelService.testExistingModel(model.id);
      } else {
        // 测试表单中的模型配置
        result = await externalModelService.testModel({
          api_type: formData.api_type,
          api_url: formData.api_url,
          model_id: formData.model_id,
          api_key: formData.api_key || undefined
        });
      }
      
      setTestResult(result);
      
      // 如果是测试已存在的模型，刷新数据列表以显示最新的测试状态
      if (model) {
        await loadModels();
      }
    } catch (err) {
      const errorMsg = err instanceof Error ? err.message : '测试失败';
      setTestResult({
        success: false,
        message: errorMsg,
        error: errorMsg
      });
    } finally {
      setTestingModel(null);
    }
  };

  const getStatusChip = (model: ExternalModel) => {
    if (!model.test_status) {
      return <Chip label="未测试" size="small" />;
    }
    
    return (
      <Chip 
        label={model.test_status === 'success' ? '正常' : '异常'} 
        color={model.test_status === 'success' ? 'success' : 'error'}
        size="small"
      />
    );
  };

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      <Box display="flex" justifyContent="space-between" alignItems="center" mb={3}>
        <Box display="flex" alignItems="center">
          <Button
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/')}
            sx={{ mr: 2 }}
          >
            返回首页
          </Button>
          <Typography variant="h4" gutterBottom sx={{ mb: 0 }}>
            外部AI模型管理
          </Typography>
        </Box>
        <Box>
          <Button
            variant="outlined"
            startIcon={<RefreshIcon />}
            onClick={loadModels}
            sx={{ mr: 2 }}
          >
            刷新
          </Button>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => handleOpenDialog()}
          >
            添加模型
          </Button>
        </Box>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>名称</TableCell>
              <TableCell>API类型</TableCell>
              <TableCell>API地址</TableCell>
              <TableCell>模型ID</TableCell>
              <TableCell>状态</TableCell>
              <TableCell>测试状态</TableCell>
              <TableCell>最后测试</TableCell>
              <TableCell>操作</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {models.length === 0 ? (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  <Typography variant="body2" color="text.secondary">
                    暂无外部模型，点击"添加模型"开始配置
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              models.map((model) => (
                <TableRow key={model.id}>
                  <TableCell>
                    <Typography variant="body2" fontWeight="bold">
                      {model.name}
                    </Typography>
                    {model.description && (
                      <Typography variant="caption" color="text.secondary">
                        {model.description}
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Chip 
                      label={getAPITypeLabel(model.api_type)} 
                      color={getAPITypeColor(model.api_type)}
                      size="small"
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {model.api_url}
                    </Typography>
                  </TableCell>
                  <TableCell>{model.model_id}</TableCell>
                  <TableCell>
                    <Chip 
                      label={model.is_active ? '启用' : '禁用'} 
                      color={model.is_active ? 'success' : 'default'}
                      size="small"
                    />
                  </TableCell>
                  <TableCell>{getStatusChip(model)}</TableCell>
                  <TableCell>
                    {model.last_tested ? (
                      <Typography variant="caption">
                        {new Date(model.last_tested).toLocaleString()}
                      </Typography>
                    ) : (
                      <Typography variant="caption" color="text.secondary">
                        从未测试
                      </Typography>
                    )}
                  </TableCell>
                  <TableCell>
                    <Tooltip title="测试连接">
                      <IconButton 
                        size="small" 
                        onClick={() => handleTest(model)}
                        disabled={testingModel === model.id}
                      >
                        {testingModel === model.id ? (
                          <CircularProgress size={16} />
                        ) : (
                          <TestIcon fontSize="small" />
                        )}
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="编辑">
                      <IconButton size="small" onClick={() => handleOpenDialog(model)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    <Tooltip title="删除">
                      <IconButton size="small" onClick={() => handleDelete(model)} color="error">
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {/* 添加/编辑对话框 */}
      <Dialog open={dialogOpen} onClose={handleCloseDialog} maxWidth="md" fullWidth>
        <DialogTitle>
          {editingModel ? '编辑外部模型' : '添加外部模型'}
        </DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="显示名称"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
                helperText="在游戏中显示的模型名称"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <FormControl fullWidth>
                <InputLabel id="api-type-label">API类型</InputLabel>
                <Select
                  labelId="api-type-label"
                  value={formData.api_type}
                  label="API类型"
                  onChange={(e) => setFormData({ ...formData, api_type: e.target.value as APIType })}
                >
                  <MenuItem value={APIType.OPENAI}>{getAPITypeLabel(APIType.OPENAI)}</MenuItem>
                  <MenuItem value={APIType.OPENWEBUI}>{getAPITypeLabel(APIType.OPENWEBUI)}</MenuItem>
                </Select>
              </FormControl>
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="API地址"
                value={formData.api_url}
                onChange={(e) => setFormData({ ...formData, api_url: e.target.value })}
                required
                placeholder={getPlaceholderURL(formData.api_type)}
                helperText="OpenAI API地址或OpenWebUI实例的API地址"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="模型ID"
                value={formData.model_id}
                onChange={(e) => setFormData({ ...formData, model_id: e.target.value })}
                required
                helperText="实际的模型标识符"
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                fullWidth
                label="API密钥"
                type="password"
                value={formData.api_key}
                onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                helperText="可选，某些API需要认证"
              />
            </Grid>
            <Grid item xs={12}>
              <TextField
                fullWidth
                label="描述"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                multiline
                rows={2}
                helperText="可选的模型描述"
              />
            </Grid>
            <Grid item xs={12}>
              <FormControlLabel
                control={
                  <Switch
                    checked={formData.is_active}
                    onChange={(e) => setFormData({ ...formData, is_active: e.target.checked })}
                  />
                }
                label="启用此模型"
              />
            </Grid>
            
            {/* 测试按钮和结果 */}
            <Grid item xs={12}>
              <Box sx={{ mt: 2, mb: 2 }}>
                <Button
                  variant="outlined"
                  startIcon={<TestIcon />}
                  onClick={() => handleTest()}
                  disabled={!formData.api_url || !formData.model_id || testingModel !== null}
                >
                  {testingModel !== null ? '测试中...' : '测试连接'}
                </Button>
              </Box>
              
              {testResult && (
                <Alert 
                  severity={testResult.success ? 'success' : 'error'}
                  sx={{ mt: 2 }}
                >
                  <Typography variant="body2">
                    {testResult.message}
                  </Typography>
                  {testResult.response_time && (
                    <Typography variant="caption">
                      响应时间: {testResult.response_time.toFixed(2)}秒
                    </Typography>
                  )}
                </Alert>
              )}
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>取消</Button>
          <Button 
            onClick={handleSave} 
            variant="contained"
            disabled={!formData.name || !formData.api_url || !formData.model_id}
          >
            {editingModel ? '更新' : '创建'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ExternalModels; 