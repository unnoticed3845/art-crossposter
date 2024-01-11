from src.dublicate_checker import DublicateChecker, cv2_hist

dc = DublicateChecker()

hash1 = dc.get_hash_from_url(
    "https://cdn.donmai.us/original/89/3b/__yuffie_kisaragi_and_don_corneo_final_fantasy_and_1_more_drawn_by_himemura_saki__893be6d2472f17a91f69b0a0bc8f43b8.jpg"
)
hash2 = dc.get_hash_from_url(
    "https://cdn.donmai.us/original/ba/c1/__yuffie_kisaragi_and_don_corneo_final_fantasy_and_1_more_drawn_by_himemura_saki__bac1ddaa48e0c985cddc3173d6350317.jpg"
)
""" hash1 = dc.get_hash("src/dublicate_checker/data/01ed1feb36225f79a2ca175370ea218a7b3ad76ad565a1dda9f3efafb4f93496.jpg")
hash2 = dc.get_hash("src/dublicate_checker/data/2100e04dd6cda792b49032466b61b8e1419329bbd472d3e0ec58fcda0e08018b.png")

hash1 = dc.get_hash("/home/kesha/Pictures/test_100.png")
hash2 = dc.get_hash("/home/kesha/Pictures/test_out_100.png") """

print(hash1)
print(hash2)
print(hash1 == hash2)
count = 0
for ch1, ch2 in zip(str(hash1), str(hash2)):
    if ch1 != ch2: count += 1
print(f"{count} different characters")