package com.projectseele.world;

import java.util.Arrays;
import java.util.UUID;

import javax.annotation.Nullable;

import com.projectseele.entity.EvaUnit01Entity;
import com.projectseele.registry.ModBlockEntities;
import com.projectseele.registry.ModItems;
import net.minecraft.core.BlockPos;
import net.minecraft.core.NonNullList;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;
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
    private final UUID[] residentWeaponIds = new UUID[SLOT_COUNT];
    private final int[] residentWeapons = new int[SLOT_COUNT];
    private int nextSlot;
    private int reservedSlot = -1;
    private long reservationNonce;
    private long lastCommittedNonce;
    private long lastReturnedNonce;
    @Nullable
    private BlockPos liftBottom;
    @Nullable
    private BlockPos liftTop;
    @Nullable
    private BlockPos surfaceFacadeOrigin;

    public EvaArmamentRackBlockEntity(BlockPos pos, BlockState state)
    {
        super(ModBlockEntities.EVA_ARMAMENT_RACK.get(), pos, state);
        Arrays.fill(this.residentWeapons, -1);
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

    /**
     * Binds this control rack to one authored physical lift shaft.  Legacy
     * hangar racks leave these fields unset and retain their compact local
     * three/25-block service lift.
     */
    public void configurePhysicalLift(BlockPos bottom, BlockPos top,
                                      @Nullable BlockPos facadeOrigin)
    {
        if (bottom.equals(this.liftBottom) && top.equals(this.liftTop)
                && java.util.Objects.equals(facadeOrigin,
                this.surfaceFacadeOrigin))
        {
            return;
        }
        this.liftBottom = bottom.immutable();
        this.liftTop = top.immutable();
        this.surfaceFacadeOrigin = facadeOrigin == null
                ? null : facadeOrigin.immutable();
        this.setChanged();
    }

    public BlockPos liftBottomOr(BlockPos fallback)
    {
        return this.liftBottom == null ? fallback : this.liftBottom;
    }

    public BlockPos liftTopOr(BlockPos fallback)
    {
        return this.liftTop == null ? fallback : this.liftTop;
    }

    @Nullable
    public BlockPos surfaceFacadeOrigin()
    {
        return this.surfaceFacadeOrigin;
    }

    public boolean insertOne(ItemStack input)
    {
        if (input.isEmpty() || weaponFor(input) < 0)
        {
            return false;
        }
        for (int slot = 0; slot < this.items.size(); slot++)
        {
            if (this.slotEmpty(slot))
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
            if (slot == this.reservedSlot)
            {
                continue;
            }
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
            if (slot == this.reservedSlot)
            {
                continue;
            }
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

    /**
     * Marks one exact slot as unavailable without removing its item.  The
     * physical payload and lift SavedData are created before commit, so a
     * crash can be reconciled without inventing a second weapon identity.
     */
    @Nullable
    public Reservation reserveNextArmament(long nonce)
    {
        if (nonce <= Math.max(this.lastCommittedNonce,
                this.lastReturnedNonce) || this.reservedSlot >= 0)
        {
            return null;
        }
        for (int offset = 0; offset < this.items.size(); offset++)
        {
            int slot = Math.floorMod(this.nextSlot + offset, this.items.size());
            int weapon = this.slotWeapon(slot);
            if (weapon >= 0)
            {
                this.reservedSlot = slot;
                this.reservationNonce = nonce;
                this.setChanged();
                ItemStack copy = this.items.get(slot).isEmpty()
                        ? stackForWeapon(weapon) : this.items.get(slot).copy();
                copy.setCount(1);
                return new Reservation(nonce, slot, copy,
                        this.residentWeaponIds[slot]);
            }
        }
        return null;
    }

    /** Allocates above every receipt owned by this rack, even if lift
     * SavedData was lost or restored from an older disk snapshot. */
    public long nextTransactionNonce(long persistedNonce)
    {
        return Math.max(Math.max(persistedNonce, this.reservationNonce),
                Math.max(this.lastCommittedNonce,
                        this.lastReturnedNonce)) + 1L;
    }

    /** Idempotent second phase of a lift presentation transaction. */
    public boolean commitReservation(long nonce, int weapon)
    {
        if (this.lastCommittedNonce == nonce)
        {
            return true;
        }
        if (this.reservedSlot < 0 || this.reservationNonce != nonce
                || this.slotWeapon(this.reservedSlot) != weapon)
        {
            return false;
        }
        this.clearSlot(this.reservedSlot);
        this.nextSlot = (this.reservedSlot + 1) % this.items.size();
        this.reservedSlot = -1;
        this.reservationNonce = 0L;
        this.lastCommittedNonce = nonce;
        this.setChanged();
        return true;
    }

    /** Recovers either side of a partially saved reservation commit. */
    public boolean reconcileReservationCommit(long nonce, int weapon)
    {
        if (this.lastCommittedNonce == nonce)
        {
            return true;
        }
        if (this.hasReservation(nonce))
        {
            return this.commitReservation(nonce, weapon);
        }
        if (this.reservedSlot >= 0)
        {
            return false;
        }
        if (!this.removeOneReservableWeapon(weapon))
        {
            // The inventory half may already be committed while its receipt
            // was not flushed. Fail closed with the payload entity retained;
            // never create or refund a second copy here.
            return false;
        }
        this.lastCommittedNonce = nonce;
        this.setChanged();
        return true;
    }

    public boolean hasReservation(long nonce)
    {
        return this.reservedSlot >= 0 && this.reservationNonce == nonce;
    }

    /** Used only when no lift SavedData entry owns the outstanding nonce. */
    public void releaseOrphanReservation()
    {
        if (this.reservedSlot >= 0)
        {
            this.reservedSlot = -1;
            this.reservationNonce = 0L;
            this.setChanged();
        }
    }

    /**
     * Inserts a returned physical payload at most once.  Replaying the bottom
     * docking tick after a save/reload cannot duplicate the weapon.
     */
    public boolean acceptReturnedArmament(long nonce, UUID entityId,
                                          int weapon)
    {
        if (nonce <= 0L || entityId == null
                || stackForWeapon(weapon).isEmpty())
        {
            return false;
        }
        if (this.lastReturnedNonce == nonce)
        {
            return this.hasResidentEntity(entityId, weapon);
        }
        if (nonce < this.lastReturnedNonce)
        {
            return false;
        }
        for (int slot = 0; slot < this.items.size(); slot++)
        {
            if (this.slotEmpty(slot))
            {
                this.residentWeaponIds[slot] = entityId;
                this.residentWeapons[slot] = weapon;
                this.lastReturnedNonce = nonce;
                this.setChanged();
                return true;
            }
        }
        return false;
    }

    public boolean hasReturnedEntity(long nonce, UUID entityId, int weapon)
    {
        return this.lastReturnedNonce == nonce
                && this.hasResidentEntity(entityId, weapon);
    }

    public record Reservation(long nonce, int slot, ItemStack stack,
                              @Nullable UUID residentEntityId) {}

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

    /** Initial payload for an Episode-3-style surface rifle station. */
    public void stockPalletRifleStation()
    {
        if (this.isEmpty())
        {
            this.insertOne(new ItemStack(ModItems.EVA_PALLET_RIFLE.get()));
            this.nextSlot = 0;
            this.setChanged();
        }
    }

    @Override
    protected void saveAdditional(CompoundTag tag)
    {
        super.saveAdditional(tag);
        ContainerHelper.saveAllItems(tag, this.items);
        tag.putInt("NextSlot", this.nextSlot);
        tag.putInt("ReservedSlot", this.reservedSlot);
        tag.putLong("ReservationNonce", this.reservationNonce);
        tag.putLong("LastCommittedNonce", this.lastCommittedNonce);
        tag.putLong("LastReturnedNonce", this.lastReturnedNonce);
        if (this.liftBottom != null && this.liftTop != null)
        {
            tag.putLong("LiftBottom", this.liftBottom.asLong());
            tag.putLong("LiftTop", this.liftTop.asLong());
        }
        if (this.surfaceFacadeOrigin != null)
        {
            tag.putLong("SurfaceFacadeOrigin",
                    this.surfaceFacadeOrigin.asLong());
        }
        ListTag residents = new ListTag();
        for (int slot = 0; slot < SLOT_COUNT; slot++)
        {
            if (this.residentWeaponIds[slot] == null)
            {
                continue;
            }
            CompoundTag resident = new CompoundTag();
            resident.putInt("Slot", slot);
            resident.putUUID("Entity", this.residentWeaponIds[slot]);
            resident.putInt("Weapon", this.residentWeapons[slot]);
            residents.add(resident);
        }
        tag.put("ResidentWeapons", residents);
    }

    @Override
    public void load(CompoundTag tag)
    {
        super.load(tag);
        this.items.clear();
        Arrays.fill(this.residentWeaponIds, null);
        Arrays.fill(this.residentWeapons, -1);
        ContainerHelper.loadAllItems(tag, this.items);
        ListTag residents = tag.getList("ResidentWeapons", Tag.TAG_COMPOUND);
        for (int index = 0; index < residents.size(); index++)
        {
            CompoundTag resident = residents.getCompound(index);
            int slot = resident.getInt("Slot");
            int weapon = resident.getInt("Weapon");
            if (slot >= 0 && slot < SLOT_COUNT
                    && resident.hasUUID("Entity")
                    && this.items.get(slot).isEmpty()
                    && !stackForWeapon(weapon).isEmpty())
            {
                this.residentWeaponIds[slot] = resident.getUUID("Entity");
                this.residentWeapons[slot] = weapon;
            }
        }
        this.nextSlot = Math.floorMod(tag.getInt("NextSlot"), this.items.size());
        int savedSlot = tag.contains("ReservedSlot")
                ? tag.getInt("ReservedSlot") : -1;
        this.reservedSlot = savedSlot >= 0 && savedSlot < this.items.size()
                && this.slotWeapon(savedSlot) >= 0 ? savedSlot : -1;
        this.reservationNonce = this.reservedSlot >= 0
                ? Math.max(0L, tag.getLong("ReservationNonce")) : 0L;
        this.lastCommittedNonce = Math.max(0L,
                tag.getLong("LastCommittedNonce"));
        this.lastReturnedNonce = Math.max(0L,
                tag.getLong("LastReturnedNonce"));
        this.liftBottom = tag.contains("LiftBottom")
                ? BlockPos.of(tag.getLong("LiftBottom")) : null;
        this.liftTop = tag.contains("LiftTop")
                ? BlockPos.of(tag.getLong("LiftTop")) : null;
        this.surfaceFacadeOrigin = tag.contains("SurfaceFacadeOrigin")
                ? BlockPos.of(tag.getLong("SurfaceFacadeOrigin")) : null;
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
        for (UUID entityId : this.residentWeaponIds)
        {
            if (entityId != null)
            {
                return false;
            }
        }
        return true;
    }

    @Override
    public ItemStack getItem(int slot)
    {
        if (slot == this.reservedSlot)
        {
            return ItemStack.EMPTY;
        }
        if (this.residentWeaponIds[slot] != null)
        {
            return stackForWeapon(this.residentWeapons[slot]);
        }
        return this.items.get(slot);
    }

    @Override
    public ItemStack removeItem(int slot, int amount)
    {
        if (slot == this.reservedSlot
                || this.residentWeaponIds[slot] != null)
        {
            return ItemStack.EMPTY;
        }
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
        if (slot == this.reservedSlot
                || this.residentWeaponIds[slot] != null)
        {
            return ItemStack.EMPTY;
        }
        return ContainerHelper.takeItem(this.items, slot);
    }

    @Override
    public void setItem(int slot, ItemStack stack)
    {
        if (slot == this.reservedSlot
                || this.residentWeaponIds[slot] != null)
        {
            return;
        }
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
        return this.residentWeaponIds[slot] == null
                && weaponFor(stack) >= 0;
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
        Arrays.fill(this.residentWeaponIds, null);
        Arrays.fill(this.residentWeapons, -1);
        this.reservedSlot = -1;
        this.reservationNonce = 0L;
        this.setChanged();
    }

    private boolean slotEmpty(int slot)
    {
        return this.items.get(slot).isEmpty()
                && this.residentWeaponIds[slot] == null;
    }

    private int slotWeapon(int slot)
    {
        return this.residentWeaponIds[slot] == null
                ? weaponFor(this.items.get(slot))
                : this.residentWeapons[slot];
    }

    private void clearSlot(int slot)
    {
        this.items.set(slot, ItemStack.EMPTY);
        this.residentWeaponIds[slot] = null;
        this.residentWeapons[slot] = -1;
    }

    private boolean removeOneReservableWeapon(int weapon)
    {
        for (int slot = 0; slot < SLOT_COUNT; slot++)
        {
            if (slot != this.reservedSlot && this.slotWeapon(slot) == weapon)
            {
                this.clearSlot(slot);
                this.setChanged();
                return true;
            }
        }
        return false;
    }

    private boolean hasResidentEntity(UUID entityId, int weapon)
    {
        for (int slot = 0; slot < SLOT_COUNT; slot++)
        {
            if (entityId.equals(this.residentWeaponIds[slot])
                    && this.residentWeapons[slot] == weapon)
            {
                return true;
            }
        }
        return false;
    }
}
