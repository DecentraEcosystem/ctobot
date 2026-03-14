import logging

logger = logging.getLogger(__name__)


def _valid_url(url) -> bool:
    return bool(url and isinstance(url, str) and url.strip().startswith('http'))


def _mc_str(mc: float) -> str:
    if not mc:
        return None
    if mc >= 1_000_000:
        return f"${mc / 1_000_000:.2f}M"
    if mc >= 1_000:
        return f"${mc / 1_000:.1f}k"
    return f"${mc:,.0f}"


async def format_token_message(
    mint: str,
    name: str,
    symbol: str,
    market_cap: float = 0,
    holders: int = None,
    price_usd: float = None,
    liquidity: float = None,
    volume1h: float = None,
    volume24h: float = None,
    txns1h: int = None,
    buys1h: int = None,
    sells1h: int = None,
    priceChange1h: float = None,
    priceChange24h: float = None,
    pairCreatedAt: float = None,
    logo_url: str = None,
    website: str = None,
    twitter: str = None,
    discord: str = None,
    telegram: str = None,
    **kwargs,
) -> str:
    """Formato unico per post organici e promo — stile CTO alert."""
    try:
        symbol = (symbol or '???').upper()
        name   = name or symbol

        # CTO extra (passati dal monitor)
        cto_claim_date  = (kwargs.get('cto_claim_date') or '')[:10]
        cto_description = kwargs.get('cto_description') or ''

        import config as _cfg
        _ch = _cfg.CHANNEL_USERNAME.lstrip('@') if _cfg.CHANNEL_USERNAME else ''

        # Se abbiamo message_id (post già salvato) usiamo il link diretto al post
        _msg_id = kwargs.get('message_id')
        if _msg_id and _ch:
            _trending_link = f"https://t.me/{_ch}/{_msg_id}"
        elif _ch:
            _trending_link = f"https://t.me/{_ch}"
        else:
            _trending_link = None

        if _trending_link:
            title_link = f"<a href='{_trending_link}'><b>${symbol} — Entered CTO Early Trending</b></a>"
        else:
            title_link = f"<b>${symbol} — Entered CTO Early Trending</b>"

        msg = f"🤝 {title_link}\n"
        msg += f"<i>{name}</i>\n\n"

        # Description (tronca a 120 chars)
        if cto_description:
            desc = cto_description[:120] + ('...' if len(cto_description) > 120 else '')
            msg += f"💬 {desc}\n\n"

        # Claim date
        if cto_claim_date:
            msg += f"📅 Claimed: <b>{cto_claim_date}</b>\n\n"

        # Market cap
        if market_cap:
            msg += f"💰 MC: <b>{_mc_str(market_cap)}</b>"
            if priceChange1h:
                arrow = "📈" if priceChange1h > 0 else "📉"
                msg += f"  {arrow} <b>{priceChange1h:+.1f}%</b>"
            msg += "\n"

        # Volume / txns
        if volume1h:
            msg += f"📊 Vol 1h: <b>{_mc_str(volume1h)}</b>\n"
        if buys1h is not None and sells1h is not None:
            msg += f"🟢 <b>{buys1h:,}</b> Buys  |  🔴 <b>{sells1h:,}</b> Sells\n"

        # Socials
        social_links = []
        if _valid_url(twitter):
            social_links.append(f"<a href='{twitter}'><b>𝕏 Twitter</b></a>")
        if _valid_url(telegram):
            social_links.append(f"<a href='{telegram}'><b>✈️ Telegram</b></a>")
        if _valid_url(website):
            social_links.append(f"<a href='{website}'><b>🌐 Website</b></a>")
        if social_links:
            msg += "\n" + "  |  ".join(social_links) + "\n"

        # Contract address
        msg += f"\n<code>{mint}</code>\n"

        # Links
        msg += f"\n<a href='https://dexscreener.com/solana/{mint}'><b>📊 DexScreener</b></a>  |  "
        msg += f"<a href='https://pump.fun/{mint}'><b>🎯 Pump.fun</b></a>"

        return msg

    except Exception as e:
        logger.error(f"format_token_message error: {e}")
        return f"🤝 ${symbol} — Community Takeover\n<code>{mint}</code>"


# format_promo_message è un alias di format_token_message — stesso formato
async def format_promo_message(
    mint: str,
    name: str,
    symbol: str,
    **kwargs,
) -> str:
    return await format_token_message(mint=mint, name=name, symbol=symbol, **kwargs)


def format_gain_alert(
    symbol: str,
    mint: str,
    milestone: float,
    initial_mc: float,
    current_mc: float,
    posted_at: float = None,
    original_post_link: str = None,
) -> str:
    if milestone < 2.0:
        label = f"+{int((milestone - 1) * 100)}%"
    else:
        label = f"{int(milestone)}x"

    if original_post_link:
        symbol_display = f"<a href='{original_post_link}'><b>${symbol}</b></a>"
        signal_display = f"<a href='{original_post_link}'>CTO Signal</a>"
    else:
        symbol_display = f"<b>${symbol}</b>"
        signal_display = "CTO Signal"

    dollar_count = 2 if milestone < 2.0 else min(int(milestone) * 2, 20)
    dollars = "💵" * dollar_count

    msg  = f"🚀 {symbol_display} is up <b>{label}</b> ⚡️\n"
    msg += f"from 📡 {signal_display}\n"
    msg += f"\n<b>{_mc_str(initial_mc)} → {_mc_str(current_mc)}</b>\n"
    msg += f"\n{dollars}\n"
    msg += f"\n<a href='https://dexscreener.com/solana/{mint}'><b>📊 DexScreener</b></a>  |  "
    msg += f"<a href='https://pump.fun/{mint}'><b>🎯 Pump.fun</b></a>"
    return msg
