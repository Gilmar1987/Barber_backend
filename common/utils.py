# common/utils.py

import re
from typing import Optional


def mask_cnpj(cnpj: Optional[str]) -> str:
    """
    Mascara CNPJ para exibição conforme LGPD.
    
    Preserva: 2 primeiros dígitos (raiz) + 4 dígitos da filial + 2 DV
    Oculta: dígitos do meio (posições 3-8)
    
    Args:
        cnpj: CNPJ com ou sem formatação (14 dígitos)
    
    Returns:
        CNPJ mascarado no formato XX.***.***/XXXX-XX
    
    Examples:
        >>> mask_cnpj("12.345.678/0001-95")
        '12.***.***/0001-95'
        >>> mask_cnpj("12345678000195")
        '12.***.***/0001-95'
        >>> mask_cnpj(None)
        '**.***.***/****-**'
    """
    if not cnpj:
        return "**.***.***/****-**"
    
    # Remove tudo que não é dígito
    cnpj_limpo = re.sub(r'\D', '', str(cnpj))
    
    if len(cnpj_limpo) != 14:
        return "**.***.***/****-**"
    
    return (
        f"{cnpj_limpo[:2]}."
        f"***."
        f"***/"
        f"{cnpj_limpo[8:12]}-"
        f"{cnpj_limpo[12:]}"
    )


def mask_cpf(cpf: Optional[str]) -> str:
    """
    Mascara CPF para exibição conforme LGPD.
    
    Preserva: 3 primeiros dígitos + 2 últimos dígitos
    Oculta: dígitos do meio
    """
    if not cpf:
        return "***.***.***-**"
    
    cpf_limpo = re.sub(r'\D', '', str(cpf))
    
    if len(cpf_limpo) != 11:
        return "***.***.***-**"
    
    return (
        f"{cpf_limpo[:3]}."
        f"***."
        f"***-"
        f"{cpf_limpo[9:]}"
    )