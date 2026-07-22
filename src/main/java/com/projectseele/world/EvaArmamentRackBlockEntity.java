package com.projectseele.world;

import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.registry.ModBlockEntities;
import com.projectseele.registry.ModItems;
import net.minecraft.core.BlockPos;
import net.minecraft.core.NonNullList;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.world.Container;
import net.minecraft.world.ContainerHelper;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.block.entity.BlockEntity;
import net.minecraft.world.level.block.state.BlockState;

/** Persistent five-slot NERV store for full-scale EVA armaments. */
public final class EvaArmamentRackBlockEntity extends BlockEntity implements Container
{
    public static final int SLOT_COUNT = 5;

    private final NonNullList<ItemStack> items =
            NonNullList.withSize(SLOT_COUNT, ItemStack.EMPTY);
    private int nextSlot;

    public EvaArmamentRackBlockEntity(BlockPos pos, BlockState state)
    {
        super(ModBlockEntities.EVA_ARMAMENT_RACK.get(), pos, state);
    }

    public static int weaponFor(ItemStack stack)
    {
        if (stack.is(ModItems.EVA_PROGRESSIVE_KNIFE.get()))
        {
            return EvaUnit01Entity.WEAPON_KNIFE;
        }
        if (stack.is(ModItems.EVA_POSITRON_CANNON.get()))
        {
            return EvaUnit01Entity.WEAPON_CANNON;
        }
        if (stack.is(ModItems.LANCE_OF_LONGINUS.get()))
        {
            return EvaUnit01Entity.WEAPON_LANCE;
        }
        if (stack.is(ModItems.EVA_PALLET_RIFLE.get()))
        {
            return EvaUnit01Entity.WEAPON_RIFLE;
        }
        if (stack.is(ModItems.EVA_N2_DEVICE.get()))
        {
            return EvaUnit01Entity.WEAPON_N2;
        }
        return -1;
    }

    public static ItemStack stackForWeapon(int weapon)
    {
        return switch (weapon)
        {
            case EvaUnit01Entity.WEAPON_KNIFE ->
                    new ItemStack(ModItems.EVA_PROGRESSIVE_KNIFE.get());
            case EvaUnit01Entity.WEAPON_CANNON ->
                    new ItemStack(ModItems.EVA_POSITRON_CANNON.get());
            case EvaUnit01Entity.WEAPON_LANCE ->
                    new ItemStack(ModItems.LANCE_OF_LONGINUS.get());
            case EvaUnit01Entity.WEAPON_RIFLE ->
                    new ItemStack(ModItems.EVA_PALLET_RIFLE.get());
            case EvaUnit01Entity.WEAPON_N2 ->
                    new ItemStack(ModItems.EVA_N2_DEVICE.get());
            default -> ItemStack.EMPTY;
        };
    }

    public boolean insertOne(ItemStack input)
    {
        if (input.isEmpty() || weaponFor(input) < 0)
        {
            return false;
        }
        for (int slot = 0; slot < this.items.size(); slot++)
        {
            if (this.items.get(slot).isEmpty())
            {
                ItemStack stored = input.copy();
                stored.setCount(1);
                this.items.set(slot, stored);
                this.setChanged();
                return true;
            }
        }
        return false;
    }

    public ItemStack takeNextArmament()
    {
        for (int offset = 0; offset < this.items.size(); offset++)
        {
            int slot = Math.floorMod(this.nextSlot + offset, this.items.size());
            ItemStack stack = this.items.get(slot);
            if (!stack.isEmpty())
            {
                this.items.set(slot, ItemStack.EMPTY);
                this.nextSlot = (slot + 1) % this.items.size();
                this.setChanged();
                return stack;
            }
        }
        return ItemStack.EMPTY;
    }

    public ItemStack removeOneWeapon(int weapon)
    {
        for (int slot = 0; slot < this.items.size(); slot++)
        {
            if (weaponFor(this.items.get(slot)) == weapon)
            {
                ItemStack removed = this.items.get(slot);
                this.items.set(slot, ItemStack.EMPTY);
                this.setChanged();
                return removed;
            }
        }
        return ItemStack.EMPTY;
    }

    /** Called only when a map upgrade has placed a brand-new rack. */
    public void stockStandardLoadout()
    {
        if (!this.isEmpty())
        {
            return;
        }
        this.insertOne(new ItemStack(ModItems.EVA_PROGRESSIVE_KNIFE.get()));
        this.insertOne(new ItemStack(ModItems.EVA_PALLET_RIFLE.get()));
        this.insertOne(new ItemStack(ModItems.EVA_POSITRON_CANNON.get()));
        this.insertOne(new ItemStack(ModItems.LANCE_OF_LONGINUS.get()));
        this.insertOne(new ItemStack(ModItems.EVA_N2_DEVICE.get()));
        this.nextSlot = 0;
        this.setChanged();
    }

    @Override
    protected void saveAdditional(CompoundTag tag)
    {
        super.saveAdditional(tag);
        ContainerHelper.saveAllItems(tag, this.items);
        tag.putInt("NextSlot", this.nextSlot);
    }

    @Override
    public void load(CompoundTag tag)
    {
        super.load(tag);
        this.items.clear();
        ContainerHelper.loadAllItems(tag, this.items);
        this.nextSlot = Math.floorMod(tag.getInt("NextSlot"), this.items.size());
    }

    @Override
    public int getContainerSize()
    {
        return this.items.size();
    }

    @Override
    public boolean isEmpty()
    {
        for (ItemStack stack : this.items)
        {
            if (!stack.isEmpty())
            {
                return false;
            }
        }
        return true;
    }

    @Override
    public ItemStack getItem(int slot)
    {
        return this.items.get(slot);
    }

    @Override
    public ItemStack removeItem(int slot, int amount)
    {
        ItemStack result = ContainerHelper.removeItem(this.items, slot, amount);
        if (!result.isEmpty())
        {
            this.setChanged();
        }
        return result;
    }

    @Override
    public ItemStack removeItemNoUpdate(int slot)
    {
        return ContainerHelper.takeItem(this.items, slot);
    }

    @Override
    public void setItem(int slot, ItemStack stack)
    {
        if (!stack.isEmpty() && weaponFor(stack) < 0)
        {
            return;
        }
        ItemStack stored = stack.copy();
        stored.setCount(Math.min(stored.getCount(), this.getMaxStackSize()));
        this.items.set(slot, stored);
        this.setChanged();
    }

    @Override
    public boolean canPlaceItem(int slot, ItemStack stack)
    {
        return weaponFor(stack) >= 0;
    }

    @Override
    public boolean stillValid(Player player)
    {
        if (this.level == null || this.level.getBlockEntity(this.worldPosition) != this)
        {
            return false;
        }
        return player.distanceToSqr(this.worldPosition.getX() + 0.5D,
                this.worldPosition.getY() + 0.5D,
                this.worldPosition.getZ() + 0.5D) <= 64.0D;
    }

    @Override
    public void clearContent()
    {
        this.items.clear();
        this.setChanged();
    }
}