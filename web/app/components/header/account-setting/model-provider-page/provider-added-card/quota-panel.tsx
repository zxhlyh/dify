import type { FC } from 'react'
import { useSWRConfig } from 'swr'
import { useTranslation } from 'react-i18next'
import type { ModelProvider } from '../declarations'
import {
  CustomConfigurationStatusEnum,
  PreferredProviderTypeEnum,
  QuotaUnitEnum,
} from '../declarations'
import {
  useAnthropicBuyQuota,
  useFreeQuota,
} from '../hooks'
import PriorityUseTip from './priority-use-tip'
import { InfoCircle } from '@/app/components/base/icons/src/vender/line/general'
import Button from '@/app/components/base/button'
import TooltipPlus from '@/app/components/base/tooltip-plus'

type QuotaPanelProps = {
  provider: ModelProvider
}
const QuotaPanel: FC<QuotaPanelProps> = ({
  provider,
}) => {
  const { t } = useTranslation()
  const { mutate } = useSWRConfig()
  const handlePay = useAnthropicBuyQuota()
  const handleFreeQuotaSuccess = () => {
    mutate('/workspaces/current/model-providers')
  }
  const handleFreeQuota = useFreeQuota(handleFreeQuotaSuccess)
  const customConfig = provider.custom_configuration
  const priorityUseType = provider.preferred_provider_type
  const systemConfig = provider.system_configuration
  const currentQuota = systemConfig.enabled && systemConfig.quota_configurations.find(item => item.quota_type === systemConfig.current_quota_type)
  const openaiOrAnthropic = ['openai', 'anthropic'].includes(provider.provider)

  return (
    <div className='group relative shrink-0 min-w-[112px] px-3 py-2 rounded-lg bg-white/[0.3] border-[0.5px] border-black/5'>
      <div className='flex items-center mb-2 h-4 text-xs font-medium text-gray-500'>
        {t('common.modelProvider.quota')}
        <TooltipPlus popupContent={
          openaiOrAnthropic
            ? t('common.modelProvider.card.tip')
            : t('common.modelProvider.quotaTip')
        }>
          <InfoCircle className='ml-0.5 w-3 h-3 text-gray-400' />
        </TooltipPlus>
      </div>
      {
        currentQuota && (
          <div className='flex items-center h-4 text-xs text-gray-500'>
            <span className='mr-0.5 text-sm font-semibold text-gray-700'>{(currentQuota?.quota_limit || 0) - (currentQuota?.quota_used || 0)}</span>
            {
              currentQuota?.quota_unit === QuotaUnitEnum.tokens && 'Tokens'
            }
            {
              currentQuota?.quota_unit === QuotaUnitEnum.times && t('common.modelProvider.callTimes')
            }
          </div>
        )
      }
      {
        !currentQuota && provider.provider === 'anthropic' && (
          <Button
            className='h-6 bg-white text-xs font-medium rounded-md'
            onClick={handlePay}
          >
            {t('common.modelProvider.buyQuota')}
          </Button>
        )
      }
      {
        !currentQuota && ['minimax', 'spark', 'zhipuai'].includes(provider.provider) && (
          <Button
            className='h-6 bg-white text-xs font-medium rounded-md'
            onClick={() => handleFreeQuota(provider.provider)}
          >
            {t('common.modelProvider.getFreeTokens')}
          </Button>
        )
      }
      {
        provider.provider === 'anthropic' && systemConfig.enabled && (
          <div
            className={`
              absolute left-0 bottom-0 hidden group-hover:flex items-center justify-center 
              w-full h-[30px] backdrop-blur-[2px] bg-gradient-to-r from-[rgba(238,244,255,0.80)] to-[rgba(237,237,240,0.70)]
              text-xs font-medium text-primary-600 cursor-pointer rounded-b-lg
            `}
            onClick={handlePay}
          >
            {t('common.modelProvider.buyQuota')}
          </div>
        )
      }
      {
        priorityUseType === PreferredProviderTypeEnum.system && customConfig.status === CustomConfigurationStatusEnum.active && (
          <PriorityUseTip />
        )
      }
    </div>
  )
}

export default QuotaPanel
