import React from 'react';
import { 
  Box, 
  Table, 
  TableBody, 
  TableCell, 
  TableContainer, 
  TableHead, 
  TableRow, 
  Paper, 
  Typography,
  Chip
} from '@mui/material';

interface VotingData {
  candidates: Array<{
    name: string;
    vote_count: number;
    voters: Array<{
      voter_name: string;
      reason: string;
    }>;
  }>;
  total_votes: number;
  total_participants: number;
}

interface VotingResultTableProps {
  votingData: VotingData;
  title?: string;
}

const VotingResultTable: React.FC<VotingResultTableProps> = ({ 
  votingData, 
  title = "投票结果" 
}) => {
  // 使用 React.useEffect 避免重复日志，只在组件挂载时输出一次
  React.useEffect(() => {
    if (process.env.NODE_ENV === 'development') {
      console.log('📊 VotingResultTable 渲染:', title, '候选人数:', votingData?.candidates?.length || 0);
    }
  }, [title, votingData?.candidates?.length]);
  
  if (!votingData.candidates.length) {
    console.log('⚠️ VotingResultTable: 无投票数据');
    return (
      <Box sx={{ p: 2, textAlign: 'center', bgcolor: '#f5f5f5', borderRadius: 2 }}>
        <Typography variant="body2" color="text.secondary">
          📊 {title}：无投票记录
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ my: 2 }}>
      <Typography variant="h6" sx={{ mb: 1, fontWeight: 'bold' }}>
        📊 {title}统计表
      </Typography>
      
      <TableContainer component={Paper} sx={{ mb: 1 }}>
        <Table size="small">
          <TableHead>
            <TableRow sx={{ bgcolor: '#fafafa' }}>
              <TableCell sx={{ fontWeight: 'bold', width: '25%' }}>被投票者</TableCell>
              <TableCell sx={{ fontWeight: 'bold', width: '15%', textAlign: 'center' }}>票数</TableCell>
              <TableCell sx={{ fontWeight: 'bold', width: '60%' }}>投票理由</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {votingData.candidates.map((candidate, index) => {
              const isTopCandidate = index === 0;
              const rowSpan = Math.max(1, candidate.voters.length);
              
              return (
                <React.Fragment key={candidate.name}>
                  <TableRow sx={{ 
                    bgcolor: isTopCandidate ? '#fff9e6' : 'inherit',
                    '& td': { borderBottom: candidate.voters.length > 1 ? 'none' : undefined }
                  }}>
                    <TableCell 
                      rowSpan={rowSpan}
                      sx={{ 
                        fontWeight: isTopCandidate ? 'bold' : 'normal',
                        color: isTopCandidate ? '#d46b08' : 'inherit',
                        verticalAlign: 'top'
                      }}
                    >
                      {candidate.name}
                    </TableCell>
                    <TableCell 
                      rowSpan={rowSpan}
                      sx={{ 
                        textAlign: 'center',
                        fontWeight: isTopCandidate ? 'bold' : 'normal',
                        color: isTopCandidate ? '#d46b08' : 'inherit',
                        verticalAlign: 'top'
                      }}
                    >
                      <Chip 
                        label={candidate.vote_count}
                        size="small"
                        color={isTopCandidate ? 'warning' : 'default'}
                        variant={isTopCandidate ? 'filled' : 'outlined'}
                      />
                    </TableCell>
                    {candidate.voters.length > 0 ? (
                      <TableCell sx={{ verticalAlign: 'top' }}>
                        <Box>
                          <Typography variant="body2" component="span" sx={{ fontWeight: 'bold', color: '#1890ff' }}>
                            {candidate.voters[0].voter_name}:
                          </Typography>
                          <Typography variant="body2" component="span" sx={{ ml: 1, color: '#666' }}>
                            {candidate.voters[0].reason}
                          </Typography>
                        </Box>
                      </TableCell>
                    ) : (
                      <TableCell sx={{ fontStyle: 'italic', color: '#999' }}>
                        无投票理由
                      </TableCell>
                    )}
                  </TableRow>
                  
                  {candidate.voters.slice(1).map((voter, voterIndex) => (
                    <TableRow key={voterIndex} sx={{ 
                      bgcolor: isTopCandidate ? '#fff9e6' : 'inherit',
                      '& td': { 
                        borderBottom: voterIndex === candidate.voters.length - 2 ? undefined : 'none'
                      }
                    }}>
                      <TableCell>
                        <Box>
                          <Typography variant="body2" component="span" sx={{ fontWeight: 'bold', color: '#1890ff' }}>
                            {voter.voter_name}:
                          </Typography>
                          <Typography variant="body2" component="span" sx={{ ml: 1, color: '#666' }}>
                            {voter.reason}
                          </Typography>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ))}
                </React.Fragment>
              );
            })}
          </TableBody>
        </Table>
      </TableContainer>
      
      <Box sx={{ 
        bgcolor: '#f5f5f5', 
        p: 1, 
        borderRadius: 1,
        fontSize: '0.875rem',
        color: '#666'
      }}>
        总投票数: {votingData.total_votes} | 参与人数: {votingData.total_participants}
      </Box>
    </Box>
  );
};

export default VotingResultTable; 