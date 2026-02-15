#!/usr/bin/env python3
"""
TESTAR API DO RAILWAY - Ver o que está sendo retornado
"""

import requests
import json

API_URL = "https://estantedoleitor.up.railway.app"

def testar_api():
    print("=" * 80)
    print("🔍 TESTE DA API RAILWAY - VERIFICAR RESPOSTA")
    print("=" * 80)
    
    # 1. Buscar todas as séries
    print("\n1️⃣  Buscando todas as séries...")
    try:
        response = requests.get(f"{API_URL}/series?per_page=1000")
        
        if response.status_code != 200:
            print(f"❌ Erro: Status {response.status_code}")
            print(response.text)
            return
        
        data = response.json()
        
        if 'items' in data:
            series_list = data['items']
        else:
            series_list = data
        
        print(f"✅ {len(series_list)} séries retornadas")
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        return
    
    # 2. Procurar por "DC K.O"
    print("\n" + "=" * 80)
    print("2️⃣  PROCURANDO 'DC K.O' NA RESPOSTA DA API")
    print("=" * 80)
    
    dc_ko_list = [s for s in series_list if 'dc k.o' in s.get('title', '').lower()]
    
    if not dc_ko_list:
        print("\n❌ 'DC K.O' não encontrada na resposta da API!")
        print("\nSéries encontradas:")
        for s in series_list[:10]:
            print(f"   • {s.get('title')} (ID: {s.get('id')})")
        return
    
    print(f"\n✅ Encontradas {len(dc_ko_list)} série(s) com 'DC K.O':\n")
    
    # 3. Analisar cada uma
    for serie in dc_ko_list:
        is_saga = serie.get('series_type') == 'saga'
        
        if is_saga:
            print("🎯 >>> SAGA ENCONTRADA <<<")
        else:
            print(f"   • {serie.get('title')}")
        
        print(f"\n📊 DADOS COMPLETOS:")
        print(json.dumps(serie, indent=2, ensure_ascii=False))
        print("\n" + "-" * 80)
        
        # Verificar campos críticos
        print("\n🔍 VERIFICAÇÃO DOS CAMPOS:")
        print(f"   series_type: {serie.get('series_type')} {'✅' if serie.get('series_type') == 'saga' else '❌'}")
        print(f"   main_issues: {serie.get('main_issues')} {'✅' if serie.get('main_issues') else '❌ (valor falsy!)'}")
        print(f"   tie_in_issues: {serie.get('tie_in_issues')} {'✅' if serie.get('tie_in_issues') else '❌ (valor falsy!)'}")
        
        # Simular lógica do JavaScript
        print("\n🎮 SIMULAÇÃO DA LÓGICA JAVASCRIPT:")
        
        series_type_ok = serie.get('series_type') == 'saga'
        main_or_tie = serie.get('main_issues') or serie.get('tie_in_issues')
        
        print(f"   series_type === 'saga': {series_type_ok}")
        print(f"   main_issues || tie_in_issues: {bool(main_or_tie)}")
        print(f"   Condição completa: {series_type_ok and bool(main_or_tie)}")
        
        if series_type_ok and main_or_tie:
            print(f"\n   ✅ BADGES SERIAM RENDERIZADOS:")
            print(f"      📖 Principais: {serie.get('main_issues', 0)}")
            print(f"      🔗 Tie-ins: {serie.get('tie_in_issues', 0)}")
        else:
            print(f"\n   ❌ BADGES NÃO SERIAM RENDERIZADOS!")
            if not series_type_ok:
                print(f"      Motivo: series_type = '{serie.get('series_type')}' (não é 'saga')")
            if not main_or_tie:
                print(f"      Motivo: main_issues={serie.get('main_issues')} e tie_in_issues={serie.get('tie_in_issues')} (ambos falsy)")
        
        print("\n" + "=" * 80 + "\n")
    
    # 4. Testar endpoint específico
    if dc_ko_list:
        saga_id = dc_ko_list[0].get('id')
        
        print("=" * 80)
        print(f"3️⃣  TESTANDO ENDPOINT ESPECÍFICO /series/{saga_id}")
        print("=" * 80)
        
        try:
            response = requests.get(f"{API_URL}/series/{saga_id}")
            
            if response.status_code == 200:
                serie_detail = response.json()
                print("\n✅ Resposta do endpoint específico:")
                print(json.dumps(serie_detail, indent=2, ensure_ascii=False))
            else:
                print(f"\n❌ Erro: Status {response.status_code}")
        except Exception as e:
            print(f"\n❌ Erro: {e}")


if __name__ == "__main__":
    try:
        testar_api()
    except KeyboardInterrupt:
        print("\n\n❌ Teste cancelado")
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
